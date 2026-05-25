from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent.parent

# -----------------------------------------------------------------------------
# Core
# -----------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY")

DEBUG = config("DEBUG", default=False, cast=bool)

ENVIRONMENT = config("ENVIRONMENT", default="development")

APP_NAME = config("APP_NAME", default="redcap-sync")
APP_VERSION = config("APP_VERSION", default="dev")

SITE_NAME = config("SITE_NAME", default="Unknown Site")
SITE_CODE = config("SITE_CODE", default="UNKNOWN")

ADMIN_URL = config("ADMIN_URL", default="admin/")

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost",
    cast=lambda v: [h.strip() for h in v.split(",") if h.strip()],
)

# -----------------------------------------------------------------------------
# Apps
# -----------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_celery_beat",
    "django_celery_results",
]

LOCAL_APPS = [
    "apps.accounts.apps.AccountsConfig",
    "apps.projects.apps.ProjectsConfig",
    "apps.sync.apps.SyncConfig",
    "apps.registry.apps.RegistryConfig",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

WSGI_APPLICATION = "config.wsgi.application"

# -----------------------------------------------------------------------------
# Templates
# -----------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
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

# -----------------------------------------------------------------------------
# Database
# -----------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": config("DB_NAME"),
        "USER": config("DB_USER"),
        "PASSWORD": config("DB_PASSWORD"),
        "HOST": config("DB_HOST", default="db"),
        "PORT": config("DB_PORT", default="5432"),
        "CONN_MAX_AGE": 60,
    }
}

# -----------------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# -----------------------------------------------------------------------------
# REST Framework
# -----------------------------------------------------------------------------
API_PAGE_SIZE = config("API_PAGE_SIZE", default=20, cast=int)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": API_PAGE_SIZE,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

# -----------------------------------------------------------------------------
# JWT
# -----------------------------------------------------------------------------
ACCESS_TOKEN_HOURS = config("ACCESS_TOKEN_HOURS", default=8, cast=int)
REFRESH_TOKEN_DAYS = config("REFRESH_TOKEN_DAYS", default=7, cast=int)

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(hours=ACCESS_TOKEN_HOURS),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=REFRESH_TOKEN_DAYS),
    "ROTATE_REFRESH_TOKENS": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# -----------------------------------------------------------------------------
# CORS / CSRF
# -----------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="",
    cast=lambda v: [o.strip() for o in v.split(",") if o.strip()],
)

CSRF_TRUSTED_ORIGINS = config(
    "CSRF_TRUSTED_ORIGINS",
    default="",
    cast=lambda v: [o.strip() for o in v.split(",") if o.strip()],
)

CORS_ALLOW_CREDENTIALS = True

# -----------------------------------------------------------------------------
# Upload limits
# -----------------------------------------------------------------------------
FILE_UPLOAD_MAX_MEMORY_SIZE = config(
    "FILE_UPLOAD_MAX_MEMORY_SIZE",
    default=104857600,
    cast=int,
)

DATA_UPLOAD_MAX_MEMORY_SIZE = config(
    "DATA_UPLOAD_MAX_MEMORY_SIZE",
    default=104857600,
    cast=int,
)

# -----------------------------------------------------------------------------
# Celery
# -----------------------------------------------------------------------------
_REDIS_BASE = config("REDIS_URL", default="redis://redis:6379")

CELERY_BROKER_URL = f"{_REDIS_BASE}/0"
CELERY_RESULT_BACKEND = f"{_REDIS_BASE}/1"

CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"

TIME_ZONE = config("TIME_ZONE", default="UTC")

CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

CELERY_RESULT_EXPIRES = config(
    "CELERY_RESULT_EXPIRES",
    default=604800,
    cast=int,
)

CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

CELERY_WORKER_MAX_TASKS_PER_CHILD = config(
    "CELERY_WORKER_MAX_TASKS_PER_CHILD",
    default=200,
    cast=int,
)

CELERY_TASK_ROUTES = {
    "sync.run_sync_job": {"queue": "default"},
    "sync.scheduled_sync_all_active": {"queue": "beat"},
}

CELERY_BEAT_SCHEDULE = {
    "nightly-sync-all-active": {
        "task": "sync.scheduled_sync_all_active",
        "schedule": crontab(hour=2, minute=0),
        "options": {"queue": "beat"},
    },
}

# -----------------------------------------------------------------------------
# R Service
# -----------------------------------------------------------------------------
R_SYNC_SERVICE_URL = config("R_SYNC_SERVICE_URL")
R_SYNC_SERVICE_API_KEY = config("R_SYNC_SERVICE_API_KEY", default="")
R_SYNC_SERVICE_TIMEOUT = config(
    "R_SYNC_SERVICE_TIMEOUT",
    default=600,
    cast=int,
)

# -----------------------------------------------------------------------------
# REDCap
# -----------------------------------------------------------------------------
REDCAP_API_URL = config("REDCAP_API_URL")

REDCAP_API_TIMEOUT = config(
    "REDCAP_API_TIMEOUT",
    default=600,
    cast=int,
)

# -----------------------------------------------------------------------------
# Encryption
# -----------------------------------------------------------------------------
REDCAP_TOKEN_ENCRYPTION_KEY = config(
    "REDCAP_TOKEN_ENCRYPTION_KEY"
)

# -----------------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------------
LANGUAGE_CODE = config("LANGUAGE_CODE", default="en-us")

USE_I18N = True
USE_TZ = True

# -----------------------------------------------------------------------------
# Static Files
# -----------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------
SESSION_COOKIE_SECURE = config(
    "SESSION_COOKIE_SECURE",
    default=False,
    cast=bool,
)

CSRF_COOKIE_SECURE = config(
    "CSRF_COOKIE_SECURE",
    default=False,
    cast=bool,
)

SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------
LOG_LEVEL = config("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}

# -----------------------------------------------------------------------------
# Misc
# -----------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"