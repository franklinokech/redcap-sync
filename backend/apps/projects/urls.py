# apps/projects/urls.py
from django.urls import path
from .views import (
    SiteListCreateView, SiteDetailView, SiteMembersView,
    SiteProjectListCreateView, SiteProjectDetailView,
    ProjectTokenView, ValidateTokenView,
)

urlpatterns = [
    # Sites
    path("sites/",                              SiteListCreateView.as_view(),     name="site-list"),
    path("sites/<int:pk>/",                     SiteDetailView.as_view(),         name="site-detail"),
    path("sites/<int:pk>/members/",             SiteMembersView.as_view(),        name="site-members"),

    # Projects
    path("",                                    SiteProjectListCreateView.as_view(), name="project-list"),
    path("<int:pk>/",                           SiteProjectDetailView.as_view(),     name="project-detail"),

    # Tokens
    path("<int:pk>/token/",                     ProjectTokenView.as_view(),       name="project-token"),
    path("<int:pk>/validate-token/",            ValidateTokenView.as_view(),      name="validate-token"),
]