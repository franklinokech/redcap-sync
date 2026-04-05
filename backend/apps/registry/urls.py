# apps/registry/urls.py
from django.urls import path
from .views import (
    CentralRegistryListCreateView,
    CentralRegistryDetailView,
    ActiveRegistryView,
    ValidateRegistryTokenView,
)

urlpatterns = [
    path("",               CentralRegistryListCreateView.as_view(), name="registry-list"),
    path("active/",        ActiveRegistryView.as_view(),             name="registry-active"),
    path("<int:pk>/",      CentralRegistryDetailView.as_view(),      name="registry-detail"),
    path("<int:pk>/validate-token/", ValidateRegistryTokenView.as_view(), name="registry-validate"),
]