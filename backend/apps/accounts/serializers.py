# apps/accounts/serializers.py
from rest_framework import serializers
from .models import User


class UserSerializer(serializers.ModelSerializer):
    """
    Full profile serializer.

    Used by:
      GET  /api/accounts/me/
      PATCH /api/accounts/me/
      GET/PATCH /api/accounts/users/<pk>/  (admin only)

    Exposes Django permission flags (is_staff, is_superuser) so the
    frontend auth store can derive isAdmin and roleLabel without a
    separate endpoint.

    is_staff and is_superuser are read-only here; an admin must use the
    Django admin panel or a dedicated promotion endpoint to change them.
    """

    class Meta:
        model  = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",           # custom: admin | site_manager | viewer
            "organisation",
            "is_staff",       # Django flag: access to /admin/
            "is_superuser",   # Django flag: all permissions bypass
            "is_active",
            "created_at",
        ]
        read_only_fields = ["id", "is_staff", "is_superuser", "created_at"]


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Admin-only serializer for POST /api/accounts/users/.
    Password is write-only and hashed via set_password() before save.
    """
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model  = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
            "organisation",
            "password",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user     = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class ChangePasswordSerializer(serializers.Serializer):
    """
    Validates a password-change request.

    old_password validation is done in the view so it has access to
    request.user.  The serializer only enforces the min-length rule on
    the new password.
    """
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
