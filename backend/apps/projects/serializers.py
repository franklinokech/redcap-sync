# apps/projects/serializers.py
from rest_framework import serializers
from .models import Site, SiteProject, APIToken


class SiteSerializer(serializers.ModelSerializer):
    project_count  = serializers.SerializerMethodField()
    member_count   = serializers.SerializerMethodField()

    class Meta:
        model  = Site
        fields = ["id", "name", "code", "description", "location",
                  "status", "project_count", "member_count", "created_at"]
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
        # Auto-assign creator as a member
        site.members.add(request.user)
        return site


class APITokenSerializer(serializers.ModelSerializer):
    token_preview = serializers.SerializerMethodField()

    class Meta:
        model  = APIToken
        fields = ["id", "label", "is_active", "token_preview", "created_at"]
        read_only_fields = ["id", "created_at", "token_preview"]

    def get_token_preview(self, obj):
        return obj.token_preview()


class APITokenCreateSerializer(serializers.Serializer):
    """Used when adding/updating a token — accepts plaintext, encrypts on save."""
    token = serializers.CharField(
        min_length=32,
        max_length=32,
        write_only=True,
        help_text="32-character REDCap API token",
    )
    label = serializers.CharField(max_length=100, required=False, allow_blank=True)


class SiteProjectSerializer(serializers.ModelSerializer):
    site_name   = serializers.CharField(source="site.name",  read_only=True)
    site_code   = serializers.CharField(source="site.code",  read_only=True)
    has_token   = serializers.SerializerMethodField()
    token       = serializers.SerializerMethodField()

    class Meta:
        model  = SiteProject
        fields = [
            "id", "site", "site_name", "site_code",
            "name", "description", "redcap_url", "project_id",
            "status", "sync_forms", "sync_fields",
            "record_id_prefix", "has_token", "token",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "site_name", "site_code", "has_token",
                            "token", "created_at", "updated_at"]

    def get_has_token(self, obj):
        return obj.has_token()

    def get_token(self, obj):
        token = obj.get_active_token()
        if token:
            return APITokenSerializer(token).data
        return None


class SiteProjectCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SiteProject
        fields = [
            "id", "site", "name", "description", "redcap_url",
            "status", "sync_forms", "sync_fields", "record_id_prefix",
        ]
        read_only_fields = ["id"]

    def create(self, validated_data):
        request = self.context["request"]
        return SiteProject.objects.create(created_by=request.user, **validated_data)