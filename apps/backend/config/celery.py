"""
Celery configuration for DBazar Backend.
Includes smart fallback if celery package is not installed in minimal environments.
"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

try:
    from celery import Celery

    app = Celery("dbazar")
    app.config_from_object("django.conf:settings", namespace="CELERY")
    app.autodiscover_tasks()
except ImportError:  # pragma: no cover
    app = None  # type: ignore[assignment]
