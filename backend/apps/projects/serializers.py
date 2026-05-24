# apps/projects/serializers.py
from __future__ import annotations

import json
from rest_framework import serializers
from .models import Site, SiteProject, APIToken


# ── helpers ───────────────────────────────────────────────────────────────────

def _decode_sync_field(value):
    """
    Always return a Python list regardless of what is stored.
    Handles: None, "", "[]", '["a","b"]', already-a-list (legacy).
    """
    if isinstance(value, list):
        return value
    if not value:
        return []
    try:
        parsed = json.loads(value)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _encode_sync_field(value):
    """
    Accept a Python list OR a JSON string and always return a JSON string
    safe to store in a TextField.
    """
    if isinstance(value, list):
        return json.dumps(value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return json.dumps(parsed)
        except (json.JSONDecodeError, TypeError):
            pass
        return json.dumps([value])
    return json.dumps([])


# ── Site ──────────────────────────────────────────────────────────────────────

class SiteSerializer(serializers.ModelSerializer):
    project_count = serializers.SerializerMethodField()
    member_count  = serializers.SerializerMethodField()

    class Meta:
        model  = Site
        fields = [
            "id", "name", "code", "description", "location",
            "status", "project_count", "member_count", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_project_count(self, obj):
        return obj.projects.count()

    def get_member_count(self, obj):
        return obj.members.count()


class SiteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Site
        fields = ["id", "name", "code", "description", "location", "status"]
        read_only_fields = ["id"]

    def create(self, validated_data):
        request = self.context["request"]
        site    = Site.objects.create(created_by=request.user, **validated_data)
        site.members.add(request.user)
        return site


# ── APIToken ──────────────────────────────────────────────────────────────────

class APITokenSerializer(serializers.ModelSerializer):
    """Read-only token metadata — never exposes plaintext."""
    token_preview = serializers.SerializerMethodField()

    class Meta:
        model  = APIToken
        fields = ["id", "label", "is_active", "token_preview", "created_at"]
        read_only_fields = ["id", "created_at", "token_preview"]

    def get_token_preview(self, obj):
        return obj.token_preview()


class APITokenCreateSerializer(serializers.Serializer):
    """
    Accepts a plaintext token for creation or rotation.
    Validation here; encryption in the view.
    """
    token = serializers.CharField(
        min_length=32,
        max_length=32,
        write_only=True,
        help_text="32-character hex REDCap API token",
    )
    label = serializers.CharField(
        max_length=100,
        required=False,
        allow_blank=True,
        default="",
    )

    def validate_token(self, value):
        cleaned = value.strip()
        if not cleaned.isalnum():
            raise serializers.ValidationError(
                "REDCap API tokens must be alphanumeric (hex string)."
            )
        return cleaned


# ── SiteProject ───────────────────────────────────────────────────────────────

class SiteProjectSerializer(serializers.ModelSerializer):
    """Full READ serializer — used for GET responses."""

    site                  = serializers.PrimaryKeyRelatedField(read_only=True)
    site_name             = serializers.CharField(source="site.name",       read_only=True)
    site_code             = serializers.CharField(source="site.code",       read_only=True)
    has_token             = serializers.SerializerMethodField()
    token                 = serializers.SerializerMethodField()
    central_registry_name = serializers.CharField(
        source="central_registry.name", read_only=True, default=None,
    )
    central_registry_url  = serializers.CharField(
        source="central_registry.redcap_url", read_only=True, default=None,
    )

    # Exposed as native lists in all responses
    sync_forms  = serializers.SerializerMethodField()
    sync_fields = serializers.SerializerMethodField()

    class Meta:
        model  = SiteProject
        fields = [
            "id", "site", "site_name", "site_code",
            "name", "description", "redcap_url", "project_id",
            "status", "sync_forms", "sync_fields", "record_id_prefix",
            "has_token", "token",
            "central_registry", "central_registry_name",
            "central_registry_url", "central_project_id",
            "created_at", "updated_at",
        ]
        read_only_fields = fields   # read-only: use CreateSerializer for writes

    def get_has_token(self, obj):
        return obj.has_token          # ← property, no ()

    def get_token(self, obj):
        t = obj.get_active_token()
        return APITokenSerializer(t).data if t else None

    def get_sync_forms(self, obj):
        return _decode_sync_field(obj.sync_forms)

    def get_sync_fields(self, obj):
        return _decode_sync_field(obj.sync_fields)


class SiteProjectCreateSerializer(serializers.ModelSerializer):
    """
    Used for POST (create) and PATCH (partial update) of SiteProject.

    sync_forms / sync_fields are accepted as:
      - a native JSON array:  []  or  ["demographics", "vitals"]
      - omitted entirely      (defaults to [])

    They are stored as a JSON string in the model TextField.
    """

    sync_forms  = serializers.JSONField(required=False, default=list)
    sync_fields = serializers.JSONField(required=False, default=list)

    class Meta:
        model  = SiteProject
        fields = [
            "id", "site", "name", "description", "redcap_url",
            "status", "sync_forms", "sync_fields", "record_id_prefix",
            "central_registry", "central_project_id",
            "created_by",
        ]
        read_only_fields = ["id", "created_by"]

    # ── Validation ────────────────────────────────────────────────────────────

    def validate_sync_forms(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a JSON array.")
        if not all(isinstance(v, str) for v in value):
            raise serializers.ValidationError("All items must be strings.")
        return value

    def validate_sync_fields(self, value):
        if not isinstance(value, list):
            raise serializers.ValidationError("Must be a JSON array.")
        if not all(isinstance(v, str) for v in value):
            raise serializers.ValidationError("All items must be strings.")
        return value

    def validate(self, attrs):
        registry   = attrs.get("central_registry")
        project_id = attrs.get("central_project_id")
        if project_id and not registry:
            raise serializers.ValidationError({
                "central_registry": (
                    "A central registry must be selected when "
                    "central_project_id is provided."
                )
            })
        return attrs

    # ── Encode lists → JSON strings before hitting the database ──────────────

    def to_internal_value(self, data):
        validated = super().to_internal_value(data)
        for field in ("sync_forms", "sync_fields"):
            if field in validated:
                validated[field] = json.dumps(validated[field])
        return validated

    # ── Decode JSON strings → lists in the response ───────────────────────────

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for field in ("sync_forms", "sync_fields"):
            rep[field] = _decode_sync_field(rep.get(field))
        return rep

    # ── Create / update ───────────────────────────────────────────────────────

    def create(self, validated_data):
        request = self.context["request"]
        return SiteProject.objects.create(created_by=request.user, **validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
