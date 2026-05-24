# apps/accounts/admin.py
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display  = ["username", "email", "first_name", "last_name",
                     "role", "organisation", "is_staff", "is_active"]
    list_filter   = ["role", "is_staff", "is_superuser", "is_active"]
    search_fields = ["username", "email", "first_name", "last_name", "organisation"]
    ordering      = ["username"]

    # ------------------------------------------------------------------ #
    # Fieldsets shown when *editing* an existing user                     #
    # ------------------------------------------------------------------ #
    fieldsets = (
        (None, {
            "fields": ("username", "password"),
        }),
        ("Personal info", {
            "fields": ("first_name", "last_name", "email"),
        }),
        ("REDCap Sync", {
            "fields": ("role", "organisation"),
        }),
        ("Permissions", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
        }),
        ("Important dates", {
            "fields": ("last_login", "date_joined"),
        }),
    )

    # ------------------------------------------------------------------ #
    # Fieldsets shown when *adding* a new user via admin                  #
    # ------------------------------------------------------------------ #
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "password1",
                "password2",
                "email",
                "first_name",
                "last_name",
                "role",
                "organisation",
                "is_staff",
                "is_active",
            ),
        }),
    )
