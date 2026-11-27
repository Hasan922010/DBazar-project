"""
Root URL configuration for DBazar Django 5 Modular Monolith.
Registers all 8 domain API modules onto the Contract-First API Router.
"""
from django.contrib import admin
from django.http import HttpRequest, JsonResponse
from django.urls import include, path

from config.api_router import api_router
from apps.iam.services import resolve_request_user

# Register bearer auth resolver
api_router.set_auth_resolver(resolve_request_user)

# Import API modules so their routes register with api_router
import apps.iam.api  # noqa: F401, E402
import apps.catalog.api  # noqa: F401, E402
import apps.inventory.api  # noqa: F401, E402
import apps.orders.api  # noqa: F401, E402
import apps.billing.api  # noqa: F401, E402
import apps.pos_sync.api  # noqa: F401, E402
import apps.integrations.api  # noqa: F401, E402
import apps.logistics.api  # noqa: F401, E402


def healthz_view(request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "status": "healthy",
            "service": "dbazar-backend",
            "version": "1.0.0",
        }
    )


urlpatterns = [
    path("", healthz_view, name="root"),
    path("admin/", admin.site.urls),
    path("healthz/", healthz_view, name="healthz"),
    path("api/v1/", include(api_router.urls)),
]
