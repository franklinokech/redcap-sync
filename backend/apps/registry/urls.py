# apps/registry/urls.py

from django.urls import path

from .views import (
    CentralRegistryListCreateView,
    CentralRegistryDetailView,
    ValidateRegistryTokenView,
)

app_name = "registry"

urlpatterns = [
    path(
        "",
        CentralRegistryListCreateView.as_view(),
        name="registry-list",
    ),
    path(
        "<int:pk>/",
        CentralRegistryDetailView.as_view(),
        name="registry-detail",
    ),
    path(
        "<int:pk>/validate-token/",
        ValidateRegistryTokenView.as_view(),
        name="registry-validate",
    ),
]
