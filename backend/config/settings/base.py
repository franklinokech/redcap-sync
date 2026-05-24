# config/settings/base.py
from datetime import timedelta
from pathlib import Path

from celery.schedules import crontab
from decouple import config

ADMIN_URL = config("ADMIN_URL", default="admin/")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY = config(
    "SECRET_KEY",
    default="change-me-in-production-use-a-long-random-string",
)

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = config(
    "ALLOWED_HOSTS",
    default="localhost,127.0.0.1",
    cast=lambda v: [h.strip() for h in v.split(",")],
)

# ---------------------------------------------------------------------------
# Apps
# ---------------------------------------------------------------------------
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

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
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

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE":   "django.db.backends.postgresql",
        "NAME":     config("DB_NAME",     default="redcap_sync"),
        "USER":     config("DB_USER",     default="postgres"),
        "PASSWORD": config("DB_PASSWORD", default="postgres"),
        "HOST":     config("DB_HOST",     default="localhost"),
        "PORT":     config("DB_PORT",     default="5432"),
    }
}

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": (
        "rest_framework.renderers.JSONRenderer",
    ),
}

# ---------------------------------------------------------------------------
# JWT
# ---------------------------------------------------------------------------
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS":  True,
    "AUTH_HEADER_TYPES":      ("Bearer",),
    "USER_ID_FIELD":          "id",
    "USER_ID_CLAIM":          "user_id",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = config(
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://localhost:3000",
    cast=lambda v: [o.strip() for o in v.split(",")],
)
CORS_ALLOW_CREDENTIALS = True

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
# Use separate Redis databases so broker queues and task results
# do not share the same keyspace.
_REDIS_BASE = config("REDIS_URL", default="redis://localhost:6379")
CELERY_BROKER_URL     = f"{_REDIS_BASE}/0"
CELERY_RESULT_BACKEND = f"{_REDIS_BASE}/1"

CELERY_ACCEPT_CONTENT    = ["json"]
CELERY_TASK_SERIALIZER   = "json"
CELERY_RESULT_SERIALIZER = "json"

# Keep in sync with TIME_ZONE below
CELERY_TIMEZONE   = "UTC"
CELERY_ENABLE_UTC = True

# Expire results after 7 days so Redis does not grow unbounded
CELERY_RESULT_EXPIRES = 60 * 60 * 24 * 7  # seconds

# Reliability: acknowledge only after the task completes;
# re-queue if the worker process is killed mid-execution
CELERY_TASK_ACKS_LATE             = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True

# Recycle worker child processes after 200 tasks to prevent memory growth
CELERY_WORKER_MAX_TASKS_PER_CHILD = 200

# Route tasks to dedicated queues so scheduled and user-triggered syncs
# do not compete for the same worker slots
CELERY_TASK_ROUTES = {
    "sync.run_sync_job":              {"queue": "default"},
    "sync.scheduled_sync_all_active": {"queue": "beat"},
}

# ---------------------------------------------------------------------------
# Celery Beat Schedule
# ---------------------------------------------------------------------------
CELERY_BEAT_SCHEDULE = {
    "nightly-sync-all-active": {
        "task":    "sync.scheduled_sync_all_active",
        "schedule": crontab(hour=2, minute=0),
        # Must match the route defined in CELERY_TASK_ROUTES above
        "options": {"queue": "beat"},
    },
}

CELERY_TASK_DEFAULT_QUEUE = "celery"
CELERY_TASK_QUEUES = None
# ---------------------------------------------------------------------------
# R Plumber sync service
# ---------------------------------------------------------------------------
# URL of the running Plumber process – no trailing slash.
# The tasks.py _make_client() helper reads these two settings.
#
# In development the R service typically listens on port 8000 (or 8080).
# Override via .env:
#
#   R_SYNC_SERVICE_URL=http://localhost:8000
#   R_SYNC_SERVICE_API_KEY=my-secret-key
#   R_SYNC_SERVICE_TIMEOUT=300
#
R_SYNC_SERVICE_URL = config(
    "R_SYNC_SERVICE_URL",
    default="http://localhost:8000",
)

# Shared secret sent as the "X-Api-Key" header.
# Leave blank ("") to disable header-based auth on the R side too.
R_SYNC_SERVICE_API_KEY = config(
    "R_SYNC_SERVICE_API_KEY",
    default="",
)

# Per-request timeout in seconds for calls to the R service.
# Sync jobs can take several minutes on large projects.
R_SYNC_SERVICE_TIMEOUT = config(
    "R_SYNC_SERVICE_TIMEOUT",
    default=300,
    cast=int,
)

# ---------------------------------------------------------------------------
# Encryption key for stored REDCap tokens
# ---------------------------------------------------------------------------
# A stable development default so the server starts without a .env file.
# MUST be overridden in production via the REDCAP_TOKEN_ENCRYPTION_KEY
# environment variable.
#
# To generate a production key:
#   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
_FERNET_DEV_DEFAULT = "H4CC0r2aiXxXzIdjtorZ9_sHEWH4TmtlAGBmlGBhC7Y="

REDCAP_TOKEN_ENCRYPTION_KEY = config(
    "REDCAP_TOKEN_ENCRYPTION_KEY",
    default=_FERNET_DEV_DEFAULT,
)

# ---------------------------------------------------------------------------
# i18n / timezone
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "UTC"
USE_I18N      = True
USE_TZ        = True

# ---------------------------------------------------------------------------
# Static files
# ---------------------------------------------------------------------------
STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ---------------------------------------------------------------------------
# Miscellaneous
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
