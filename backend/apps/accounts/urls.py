# apps/accounts/urls.py
from django.urls import path
from .views import MeView, ChangePasswordView, UserListView, UserDetailView

urlpatterns = [
    path("me/",                  MeView.as_view(),             name="me"),
    path("me/change-password/",  ChangePasswordView.as_view(), name="change-password"),
    path("users/",               UserListView.as_view(),        name="user-list"),
    path("users/<int:pk>/",      UserDetailView.as_view(),      name="user-detail"),
]