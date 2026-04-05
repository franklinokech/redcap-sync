# apps/sync/serializers.py
from rest_framework import serializers
from .models import SyncJob, SyncLog


class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SyncLog
        fields = ["id", "level", "message", "detail", "timestamp"]
        read_only_fields = fields


class SyncJobSerializer(serializers.ModelSerializer):
    site_project_name = serializers.CharField(source="site_project.name",      read_only=True)
    site_name         = serializers.CharField(source="site_project.site.name", read_only=True)
    site_code         = serializers.CharField(source="site_project.site.code", read_only=True)
    registry_name     = serializers.CharField(source="registry.name",          read_only=True)
    triggered_by_name = serializers.CharField(source="triggered_by.username",  read_only=True)
    date_range        = serializers.CharField(source="date_range_display",      read_only=True)
    log_count         = serializers.SerializerMethodField()

    class Meta:
        model  = SyncJob
        fields = [
            "id",
            "site_project", "site_project_name", "site_name", "site_code",
            "registry", "registry_name",
            "sync_type", "date_from", "date_to", "date_range",
            "status", "records_pulled", "records_pushed",
            "duration_secs", "error_message",
            "triggered_by", "triggered_by_name",
            "started_at", "completed_at", "created_at",
            "log_count",
        ]
        read_only_fields = [
            "id", "status", "records_pulled", "records_pushed",
            "duration_secs", "error_message", "celery_task_id",
            "started_at", "completed_at", "created_at",
        ]

    def get_log_count(self, obj):
        return obj.logs.count()


class TriggerSyncSerializer(serializers.Serializer):
    """Validates the payload for POST /api/sync/trigger/"""
    site_project = serializers.IntegerField(help_text="SiteProject ID to sync")
    registry     = serializers.IntegerField(
        required=False,
        help_text="CentralRegistry ID — defaults to the active registry if omitted",
    )
    sync_type    = serializers.ChoiceField(
        choices=["full", "partial"],
        default="full",
    )
    date_from    = serializers.DateField(required=False, allow_null=True)
    date_to      = serializers.DateField(required=False, allow_null=True)

    def validate(self, data):
        if data.get("sync_type") == "partial":
            if not data.get("date_from") or not data.get("date_to"):
                raise serializers.ValidationError(
                    "date_from and date_to are required for partial sync."
                )
            if data["date_from"] > data["date_to"]:
                raise serializers.ValidationError(
                    "date_from must be before or equal to date_to."
                )
        return data