# config/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

urlpatterns = [
    path("admin/",               admin.site.urls),

    # JWT auth
    path("api/auth/token/",         TokenObtainPairView.as_view(),  name="token_obtain_pair"),
    path("api/auth/token/refresh/", TokenRefreshView.as_view(),     name="token_refresh"),
    path("api/auth/token/verify/",  TokenVerifyView.as_view(),      name="token_verify"),

    # App routes
    path("api/accounts/",  include("apps.accounts.urls")),
    path("api/projects/",  include("apps.projects.urls")),
    path("api/sync/",      include("apps.sync.urls")),
    path("api/registry/",  include("apps.registry.urls")),
]