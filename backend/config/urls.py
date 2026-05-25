# config/urls.py
"""
Project-wide URL configuration.

Layout
------
/admin/                     Django admin (path configurable via ADMIN_URL env var)
/api/auth/                  JWT token obtain / refresh / verify
/api/accounts/              User registration, profile, password
/api/projects/              Sites, SiteProjects, API tokens
/api/sync/                  Sync jobs, logs, stats
/api/registry/              Central REDCap registries
/api/health/                Lightweight liveness probe (no DB hit)
"""

from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)


# ---------------------------------------------------------------------------
# Liveness probe
# ---------------------------------------------------------------------------
def health_check(request):  # noqa: ARG001
    """Return 200 OK with a JSON body.

    Intentionally avoids any database query so it stays fast even when
    the database is under load.  Use a separate ``/api/ready/`` endpoint
    if you need a database-touching readiness probe.
    """
    return JsonResponse({"status": "ok"})


# ---------------------------------------------------------------------------
# URL patterns
# ---------------------------------------------------------------------------
# The admin URL defaults to "admin/" but can be changed via the ADMIN_URL
# environment variable so production deployments are harder to discover.
_admin_url = getattr(settings, "ADMIN_URL", "admin/")

urlpatterns = [
    # Admin
    path(_admin_url, admin.site.urls),

    # JWT authentication
    path("api/auth/token/",         TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(),    name="token_refresh"),
    path("api/auth/token/verify/",  TokenVerifyView.as_view(),     name="token_verify"),

    # Application routes
    path("api/accounts/",  include("apps.accounts.urls")),
    path("api/projects/",  include("apps.projects.urls")),
    path("api/sync/",      include("apps.sync.urls")),
    path("api/registry/",  include("apps.registry.urls")),

    # Infrastructure
    path("api/health/", health_check, name="health_check"),
]


# ---------------------------------------------------------------------------
# JSON error handlers
# ---------------------------------------------------------------------------
# These replace Django's default HTML error pages so API clients always
# receive JSON, even for unhandled 404 / 500 errors.

def _handler404(request, exception):  # noqa: ARG001
    return JsonResponse(
        {"detail": "The requested resource was not found."},
        status=404,
    )


def _handler500(request):  # noqa: ARG001
    return JsonResponse(
        {"detail": "An internal server error occurred."},
        status=500,
    )


handler404 = _handler404
handler500 = _handler500
