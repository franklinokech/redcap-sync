# apps/projects/urls.py

from django.urls import path

from .views import (
    SiteListCreateView,
    SiteDetailView,
    SiteMembersView,
    SiteProjectListCreateView,
    SiteProjectDetailView,
    LinkRegistryView,
    ProjectTokenView,
    ValidateTokenView,
)

app_name = "projects"

urlpatterns = [
    # --- Sites -----------------------------------------------------------
    path("sites/",                   SiteListCreateView.as_view(),        name="site-list"),
    path("sites/<int:pk>/",          SiteDetailView.as_view(),            name="site-detail"),
    path("sites/<int:pk>/members/",  SiteMembersView.as_view(),           name="site-members"),

    # --- Projects --------------------------------------------------------
    # NOTE: the empty-string route must come before any <int:pk> routes so
    # Django does not attempt to match "" as a project pk.
    path("",                         SiteProjectListCreateView.as_view(), name="project-list"),
    path("<int:pk>/",                SiteProjectDetailView.as_view(),     name="project-detail"),
    path("<int:pk>/link-registry/",  LinkRegistryView.as_view(),          name="link-registry"),

    # --- Tokens ----------------------------------------------------------
    path("<int:pk>/token/",          ProjectTokenView.as_view(),          name="project-token"),
    path("<int:pk>/validate-token/", ValidateTokenView.as_view(),         name="validate-token"),
]
