"""
ASGI config for DBazar project.
Supports HTTP and Django Channels WebSocket (for real-time Logistics GPS & VMI telemetry).
"""
import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django_asgi_app = get_asgi_application()

try:
    from channels.routing import ProtocolTypeRouter, URLRouter
    from django.urls import path
    from apps.logistics.consumers import LogisticsGpsConsumer

    application = ProtocolTypeRouter(
        {
            "http": django_asgi_app,
            "websocket": URLRouter(
                [
                    path("ws/logistics/shipments/<uuid:shipment_id>/gps/", LogisticsGpsConsumer.as_asgi()),
                ]
            ),
        }
    )
except ImportError:  # pragma: no cover
    application = django_asgi_app
