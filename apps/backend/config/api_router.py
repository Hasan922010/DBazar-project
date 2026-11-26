"""
Contract-First Pydantic v2 REST API Router for Django 5 (Ninja-compatible).
Provides:
- Type-safe Pydantic v2 request/response validation
- Bearer JWT Authentication & Organization RBAC context injection
- Standardized error envelopes with X-Correlation-ID
- Automatic OpenAPI 3.1.0 specification generator (`export_openapi`)
"""
from __future__ import annotations

import functools
import inspect
import json
import re
import uuid
from typing import Any, Callable, Dict, List, Optional, Type, get_type_hints

from django.http import HttpRequest, JsonResponse
from django.urls import URLPattern, path
from django.views.decorators.csrf import csrf_exempt
from pydantic import BaseModel, ValidationError


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details


class ErrorResponseSchema(BaseModel):
    error_code: str
    message: str
    correlation_id: str
    details: Optional[Any] = None


class RouteSpec:
    def __init__(
        self,
        method: str,
        route_path: str,
        operation_id: str,
        summary: str,
        tags: List[str],
        request_model: Optional[Type[BaseModel]],
        response_model: Optional[Type[BaseModel]],
        status_code: int,
        auth_required: bool,
        handler: Callable[..., Any],
    ) -> None:
        self.method = method.upper()
        self.route_path = route_path
        self.operation_id = operation_id
        self.summary = summary
        self.tags = tags
        self.request_model = request_model
        self.response_model = response_model
        self.status_code = status_code
        self.auth_required = auth_required
        self.handler = handler
        self.signature = inspect.signature(handler)


class ContractAPIRouter:
    """
    Lightweight, deterministic Django 5 + Pydantic v2 API Router with OpenAPI 3.1 generation.
    """

    def __init__(self, title: str, version: str, description: str = "") -> None:
        self.title = title
        self.version = version
        self.description = description
        self.routes: List[RouteSpec] = []
        self._path_handlers: Dict[str, Dict[str, RouteSpec]] = {}
        self._auth_resolver: Optional[Callable[[HttpRequest], Any]] = None

    def set_auth_resolver(self, resolver: Callable[[HttpRequest], Any]) -> None:
        self._auth_resolver = resolver

    def route(
        self,
        method: str,
        route_path: str,
        *,
        response: Optional[Type[BaseModel]] = None,
        request_body: Optional[Type[BaseModel]] = None,
        status_code: int = 200,
        tags: Optional[List[str]] = None,
        summary: str = "",
        auth: bool = True,
        operation_id: Optional[str] = None,
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
            op_id = operation_id or func.__name__
            req_model = request_body
            if req_model is None:
                hints = get_type_hints(func)
                for param_name, hint in hints.items():
                    if param_name in ("payload", "body", "data") and isinstance(hint, type) and issubclass(hint, BaseModel):
                        req_model = hint
                        break

            spec = RouteSpec(
                method=method,
                route_path=route_path,
                operation_id=op_id,
                summary=summary or (func.__doc__ or "").strip() or op_id,
                tags=tags or ["default"],
                request_model=req_model,
                response_model=response,
                status_code=status_code,
                auth_required=auth,
                handler=func,
            )
            self.routes.append(spec)
            norm_path = route_path.lstrip("/")
            self._path_handlers.setdefault(norm_path, {})[method.upper()] = spec
            return func

        return decorator

    def get(self, route_path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route("GET", route_path, **kwargs)

    def post(self, route_path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route("POST", route_path, **kwargs)

    def put(self, route_path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route("PUT", route_path, **kwargs)

    def patch(self, route_path: str, **kwargs: Any) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        return self.route("PATCH", route_path, **kwargs)

    def _serialize(self, obj: Any) -> Any:
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")
        if isinstance(obj, list):
            return [self._serialize(item) for item in obj]
        if isinstance(obj, dict):
            return {k: self._serialize(v) for k, v in obj.items()}
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return obj

    def _make_django_view(self, methods_map: Dict[str, RouteSpec]) -> Callable[..., JsonResponse]:
        @csrf_exempt
        def view(request: HttpRequest, **path_kwargs: Any) -> JsonResponse:
            correlation_id = getattr(request, "correlation_id", str(uuid.uuid4()))
            method = (request.method or "GET").upper()
            spec = methods_map.get(method)
            if spec is None:
                return JsonResponse(
                    {
                        "error_code": "METHOD_NOT_ALLOWED",
                        "message": f"Method {method} not allowed.",
                        "correlation_id": correlation_id,
                    },
                    status=405,
                )

            try:
                if spec.auth_required and self._auth_resolver is not None:
                    user = self._auth_resolver(request)
                    if user is None:
                        raise ApiError(401, "UNAUTHORIZED", "Avtorizatsiya talab qilinadi (Bearer token).")
                    request.user = user

                call_kwargs: Dict[str, Any] = dict(path_kwargs)
                if spec.request_model is not None:
                    try:
                        raw_body = request.body.decode("utf-8") if request.body else "{}"
                        json_data = json.loads(raw_body or "{}")
                    except json.JSONDecodeError as exc:
                        raise ApiError(400, "INVALID_JSON", f"Noto'g'ri JSON formati: {exc}") from exc

                    try:
                        payload_obj = spec.request_model.model_validate(json_data)
                    except ValidationError as exc:
                        raise ApiError(
                            422,
                            "VALIDATION_ERROR",
                            "Ma'lumotlar tekshiruvdan o'tmadi.",
                            details=exc.errors(),
                        ) from exc

                    for param_name in ("payload", "body", "data"):
                        if param_name in spec.signature.parameters:
                            call_kwargs[param_name] = payload_obj
                            break

                # Inject query parameters if expected by handler signature
                for p_name, p_obj in spec.signature.parameters.items():
                    if p_name == "request" or p_name in call_kwargs:
                        continue
                    if p_name in request.GET:
                        val: Any = request.GET.get(p_name)
                        if p_obj.annotation is int and val is not None:
                            val = int(val)
                        elif p_obj.annotation is bool and val is not None:
                            val = val.lower() in ("1", "true", "yes")
                        call_kwargs[p_name] = val

                result = spec.handler(request, **call_kwargs)
                if spec.response_model is not None and isinstance(result, dict):
                    result = spec.response_model.model_validate(result)
                serialized = self._serialize(result)
                return JsonResponse(serialized, status=spec.status_code, safe=isinstance(serialized, dict))

            except ApiError as err:
                return JsonResponse(
                    {
                        "error_code": err.code,
                        "message": err.message,
                        "correlation_id": correlation_id,
                        "details": err.details,
                    },
                    status=err.status_code,
                )
            except ValueError as err:
                return JsonResponse(
                    {
                        "error_code": "BAD_REQUEST",
                        "message": str(err),
                        "correlation_id": correlation_id,
                    },
                    status=400,
                )

        return view

    @property
    def urls(self) -> List[URLPattern]:
        patterns: List[URLPattern] = []
        for norm_path, methods_map in self._path_handlers.items():
            # Convert OpenAPI {id} or Django <str:id> to Django path syntax
            django_path = re.sub(r"\{(\w+)\}", r"<str:\1>", norm_path)
            patterns.append(path(django_path, self._make_django_view(methods_map)))

        # Built-in OpenAPI JSON endpoint
        @csrf_exempt
        def openapi_json_view(request: HttpRequest) -> JsonResponse:
            return JsonResponse(self.generate_openapi_schema())

        patterns.append(path("openapi.json", openapi_json_view))
        return patterns

    def generate_openapi_schema(self) -> Dict[str, Any]:
        components_schemas: Dict[str, Any] = {
            "ErrorResponseSchema": ErrorResponseSchema.model_json_schema(ref_template="#/components/schemas/{model}")
        }
        paths: Dict[str, Dict[str, Any]] = {}

        def register_model(model_cls: Type[BaseModel]) -> str:
            name = model_cls.__name__
            schema = model_cls.model_json_schema(ref_template="#/components/schemas/{model}")
            defs = schema.pop("$defs", {})
            for def_name, def_schema in defs.items():
                components_schemas[def_name] = def_schema
            components_schemas[name] = schema
            return f"#/components/schemas/{name}"

        for spec in self.routes:
            openapi_path = "/api/v1/" + spec.route_path.lstrip("/")
            # Convert Django <type:name> to {name} if present
            openapi_path = re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", openapi_path)
            path_item = paths.setdefault(openapi_path, {})

            parameters: List[Dict[str, Any]] = [
                {
                    "name": "X-Correlation-ID",
                    "in": "header",
                    "required": False,
                    "schema": {"type": "string", "format": "uuid"},
                }
            ]
            for match in re.finditer(r"\{(\w+)\}", openapi_path):
                p_name = match.group(1)
                parameters.append(
                    {
                        "name": p_name,
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    }
                )

            operation: Dict[str, Any] = {
                "operationId": spec.operation_id,
                "summary": spec.summary,
                "tags": spec.tags,
                "parameters": parameters,
                "responses": {
                    str(spec.status_code): {
                        "description": "Successful operation",
                    },
                    "400": {
                        "description": "Bad Request",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponseSchema"}}},
                    },
                    "401": {
                        "description": "Unauthorized",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponseSchema"}}},
                    },
                    "422": {
                        "description": "Validation Error",
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/ErrorResponseSchema"}}},
                    },
                },
            }

            if spec.auth_required:
                operation["security"] = [{"bearerAuth": []}]

            if spec.request_model is not None:
                ref = register_model(spec.request_model)
                operation["requestBody"] = {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": ref},
                        }
                    },
                }

            if spec.response_model is not None:
                ref = register_model(spec.response_model)
                operation["responses"][str(spec.status_code)]["content"] = {
                    "application/json": {
                        "schema": {"$ref": ref},
                    }
                }

            path_item[spec.method.lower()] = operation

        return {
            "openapi": "3.1.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": self.description,
            },
            "paths": paths,
            "components": {
                "securitySchemes": {
                    "bearerAuth": {
                        "type": "http",
                        "scheme": "bearer",
                        "bearerFormat": "JWT",
                    }
                },
                "schemas": components_schemas,
            },
        }


api_router = ContractAPIRouter(
    title="DBazar B2B Supply Chain, VMI & Offline-First Cloud POS API",
    version="1.0.0",
    description="Contract-First OpenAPI 3.1 specification generated from Django 5 + Pydantic v2 schemas.",
)
