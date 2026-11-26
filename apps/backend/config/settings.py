"""
Django 5 Settings for DBazar Modular Monolith Backend.
Follows GEMINI.md and apps/backend/AGENTS.md architecture rules.
"""
import importlib.util
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get(
    "DJANGO_SECRET_KEY",
    "django-insecure-dbazar-dev-secret-key-change-in-production-9f8e7d6c5b4a",
)

DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

HAS_UNFOLD = importlib.util.find_spec("unfold") is not None
HAS_CHANNELS = importlib.util.find_spec("channels") is not None

INSTALLED_APPS = [
    *(["unfold"] if HAS_UNFOLD else []),
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    *(["channels"] if HAS_CHANNELS else []),
    # DBazar Modular Monolith Domain Apps
    "apps.iam",
    "apps.catalog",
    "apps.inventory",
    "apps.orders",
    "apps.billing",
    "apps.pos_sync",
    "apps.integrations",
    "apps.logistics",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "config.middleware.CorrelationIdMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# Database configuration: PostgreSQL 16 primary, with SQLite option for isolated local/CI runs
DB_ENGINE = os.environ.get("DB_ENGINE", "sqlite" if os.environ.get("USE_SQLITE", "1") == "1" else "postgresql")

if DB_ENGINE == "postgresql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.environ.get("POSTGRES_DB", "dbazar_dev"),
            "USER": os.environ.get("POSTGRES_USER", "dbazar"),
            "PASSWORD": os.environ.get("POSTGRES_PASSWORD", "dbazar"),
            "HOST": os.environ.get("POSTGRES_HOST", "localhost"),
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "CONN_MAX_AGE": 60,
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_USER_MODEL = "iam.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "uz"
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Redis & Celery Configuration
REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)
CELERY_TASK_ALWAYS_EAGER = os.environ.get("CELERY_TASK_ALWAYS_EAGER", "true").lower() in ("1", "true")

# Channels Layer
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    }
}

# Unfold Admin Panel Configuration
UNFOLD = {
    "SITE_TITLE": "DBazar Back-Office Admin",
    "SITE_HEADER": "DBazar B2B & Cloud POS",
    "SITE_SYMBOL": "storefront",
}

# Contracts OpenAPI output path
OPENAPI_CONTRACT_PATH = BASE_DIR.parent.parent / "packages" / "contracts" / "openapi.yaml"
