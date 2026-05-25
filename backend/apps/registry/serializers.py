# apps/registry/serializers.py

from __future__ import annotations

import re
from typing import Any
from rest_framework import serializers
from .models import CentralRegistry

_MISSING = object()          # sentinel -- distinct from None and ""


class CentralRegistrySerializer(serializers.ModelSerializer):
    """
    Read serializer -- used for list/retrieve responses.
    """

    token_preview         = serializers.SerializerMethodField()
    has_token             = serializers.SerializerMethodField()
    linked_projects_count = serializers.SerializerMethodField()
    created_by            = serializers.StringRelatedField(read_only=True)

    class Meta:
        model  = CentralRegistry
        fields = [
            "id",
            "name",
            "description",
            "redcap_url",
            "project_id",
            "overwrite_with_blanks",
            "has_token",
            "token_preview",
            "linked_projects_count",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "project_id",
            "has_token",
            "token_preview",
            "linked_projects_count",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_has_token(self, obj: CentralRegistry) -> bool:
        return obj.has_token

    def get_token_preview(self, obj: CentralRegistry) -> str:
        return obj.token_preview       # @property, not obj.token_preview()

    def get_linked_projects_count(self, obj: CentralRegistry) -> int:
        return obj.linked_projects_count


class CentralRegistryCreateSerializer(serializers.ModelSerializer):
    """
    Write serializer -- used for create (POST) and update (PATCH/PUT).

    Token is write-only:
    - required on create (enforced in validate())
    - optional on PATCH (omit to keep existing token)
    """

    token = serializers.CharField(
        min_length=32,
        max_length=32,
        write_only=True,
        required=False,
        allow_blank=False,
        help_text="32-character hex REDCap API token for the registry project",
    )

    class Meta:
        model  = CentralRegistry
        fields = [
            "id",
            "name",
            "description",
            "redcap_url",
            "overwrite_with_blanks",
            "token",
        ]
        read_only_fields = ["id"]

    # ------------------------------------------------------------------
    # Field-level validation
    # ------------------------------------------------------------------

    def validate_token(self, value: str) -> str:
        """Strip whitespace, enforce 32-char hex."""
        value = value.strip()
        if len(value) != 32:
            raise serializers.ValidationError(
                "Token must be exactly 32 characters after stripping whitespace."
            )
        if not re.fullmatch(r"[a-fA-F0-9]{32}", value):
            raise serializers.ValidationError(
                "Token must contain only hexadecimal characters (0-9, a-f, A-F)."
            )
        return value

    # ------------------------------------------------------------------
    # Object-level validation
    # ------------------------------------------------------------------

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Enforce token presence on create; optional on update."""
        if self.instance is None and not attrs.get("token"):
            raise serializers.ValidationError(
                {"token": "A token is required when creating a registry."}
            )
        return attrs

    # ------------------------------------------------------------------
    # Create / Update
    # ------------------------------------------------------------------

    def create(self, validated_data: dict[str, Any]) -> CentralRegistry:
        # validate() guarantees "token" is present on create
        token_value: str = validated_data.pop("token")
        request          = self.context.get("request")
        registry         = CentralRegistry(
            created_by=request.user if request else None,
            **validated_data,
        )
        registry.set_token(token_value)
        registry.save()
        return registry

    def update(
        self, instance: CentralRegistry, validated_data: dict[str, Any]
    ) -> CentralRegistry:
        # Use the sentinel so pop() return type is str | object, not str | None
        token_value = validated_data.pop("token", _MISSING)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Only update the token if the caller explicitly supplied one
        if token_value is not _MISSING:
            # At this point token_value came through validate_token(),
            # so it is a clean 32-char hex str -- narrow the type for the IDE
            assert isinstance(token_value, str), "token_value must be str"  # noqa: S101
            instance.set_token(token_value)

        instance.save()
        return instance
