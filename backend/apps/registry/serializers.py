# apps/registry/serializers.py
from rest_framework import serializers
from .models import CentralRegistry


class CentralRegistrySerializer(serializers.ModelSerializer):
    token_preview = serializers.SerializerMethodField()

    class Meta:
        model  = CentralRegistry
        fields = [
            "id", "name", "description", "redcap_url", "project_id",
            "is_active", "overwrite_with_blanks",
            "token_preview", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "token_preview", "created_at", "updated_at"]

    def get_token_preview(self, obj):
        return obj.token_preview()


class CentralRegistryCreateSerializer(serializers.ModelSerializer):
    token = serializers.CharField(
        min_length=32, max_length=32, write_only=True,
        help_text="32-character REDCap API token for the registry",
    )

    class Meta:
        model  = CentralRegistry
        fields = [
            "id", "name", "description", "redcap_url",
            "is_active", "overwrite_with_blanks", "token",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        token_value = validated_data.pop("token")
        request     = self.context["request"]
        registry    = CentralRegistry(created_by=request.user, **validated_data)
        registry.set_token(token_value)
        registry.save()
        return registry

    def update(self, instance, validated_data):
        token_value = validated_data.pop("token", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if token_value:
            instance.set_token(token_value)
        instance.save()
        return instance