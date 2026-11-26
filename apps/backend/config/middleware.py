"""
Observability & Security Middleware for DBazar Backend.
Attaches X-Correlation-ID to every request and response.
"""
import uuid
from typing import Callable
from django.http import HttpRequest, HttpResponse


class CorrelationIdMiddleware:
    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
        request.correlation_id = correlation_id  # type: ignore[attr-defined]
        response = self.get_response(request)
        response["X-Correlation-ID"] = correlation_id
        return response
