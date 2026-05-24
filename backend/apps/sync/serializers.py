# apps/sync/serializers.py

from __future__ import annotations

from django.utils import timezone
from rest_framework import serializers

from .models import SyncJob, SyncLog


# ---------------------------------------------------------------------------
# Log
# ---------------------------------------------------------------------------


class SyncLogSerializer(serializers.ModelSerializer):
    class Meta:
        model  = SyncLog
        fields = ["id", "level", "message", "detail", "timestamp"]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Job — list (lightweight, no nested logs)
# ---------------------------------------------------------------------------


class SyncJobListSerializer(serializers.ModelSerializer):
    """
    Lightweight read serializer for list endpoints.

    Omits nested logs and snapshot blobs to keep list responses small.
    ``log_count`` prefers a queryset annotation to avoid N+1 queries.
    """

    site_project_name = serializers.CharField(
        source="site_project.name", read_only=True
    )
    site_name = serializers.CharField(
        source="site_project.site.name", read_only=True
    )
    registry_name = serializers.CharField(
        source="registry.name", read_only=True
    )
    triggered_by_name = serializers.CharField(
        source="triggered_by.username", read_only=True, allow_null=True
    )
    is_cancellable = serializers.BooleanField(read_only=True)
    log_count      = serializers.SerializerMethodField()

    class Meta:
        model  = SyncJob
        fields = [
            "id",
            "site_project", "site_project_name", "site_name",
            "registry",     "registry_name",
            "sync_type", "status", "is_cancellable",
            "records_pulled", "records_pushed", "records_skipped",
            "duration_secs", "error_message",
            "triggered_by", "triggered_by_name",
            "started_at", "completed_at", "created_at",
            "log_count",
        ]
        read_only_fields = fields

    def get_log_count(self, obj: SyncJob) -> int:
        # Use queryset annotation when available; fall back to a counted query.
        # NOTE: check `is not None` so that a legitimate count of 0 is not
        # treated as falsy and discarded.
        annotated = getattr(obj, "log_count_annotated", None)
        if annotated is not None:
            return int(annotated)
        return obj.logs.count()


# ---------------------------------------------------------------------------
# Job — detail (includes nested logs, snapshot fields, summary)
# ---------------------------------------------------------------------------


class SyncJobDetailSerializer(SyncJobListSerializer):
    """
    Full serializer for single-job detail endpoints.

    Extends the list serializer with:
    - Nested log entries
    - Snapshot fields (forms / fields scoping captured at trigger time)
    - The model ``summary`` property
    - ``date_range`` display string
    """

    date_range = serializers.CharField(source="date_range_display", read_only=True)
    summary    = serializers.DictField(read_only=True)
    logs       = SyncLogSerializer(many=True, read_only=True)

    class Meta(SyncJobListSerializer.Meta):
        fields = SyncJobListSerializer.Meta.fields + [
            "date_from", "date_to", "date_range",
            "forms_snapshot", "fields_snapshot",
            "celery_task_id",
            "summary",
            "logs",
        ]
        read_only_fields = fields


# ---------------------------------------------------------------------------
# Trigger
# ---------------------------------------------------------------------------


class TriggerSyncSerializer(serializers.Serializer):
    """Validates the request payload for POST /api/sync/trigger/<pk>/"""

    sync_type = serializers.ChoiceField(
        choices=SyncJob.SyncType.choices,
        default=SyncJob.SyncType.FULL,
    )
    date_from = serializers.DateField(required=False, allow_null=True)
    date_to   = serializers.DateField(required=False, allow_null=True)

    # registry is resolved from the SiteProject in the view;
    # accepting it here allows an override (power-user flow).
    registry = serializers.IntegerField(
        required=False,
        allow_null=True,
        help_text="Override the registry linked to the project (optional).",
    )

    def validate(self, data: dict) -> dict:
        sync_type = data.get("sync_type", SyncJob.SyncType.FULL)
        date_from = data.get("date_from")
        date_to   = data.get("date_to")
        today     = timezone.localdate()

        if sync_type == SyncJob.SyncType.PARTIAL:
            if not date_from and not date_to:
                raise serializers.ValidationError(
                    "A partial sync requires at least one of date_from or date_to."
                )
            if date_from and date_to and date_from > date_to:
                raise serializers.ValidationError(
                    {"date_to": "date_to must be on or after date_from."}
                )
            if date_from and date_from > today:
                raise serializers.ValidationError(
                    {"date_from": "date_from cannot be in the future."}
                )
            if date_to and date_to > today:
                raise serializers.ValidationError(
                    {"date_to": "date_to cannot be in the future."}
                )

        if sync_type == SyncJob.SyncType.FULL and (date_from or date_to):
            raise serializers.ValidationError(
                "date_from / date_to are only valid with sync_type='partial'."
            )

        return data


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


class PreviewSyncSerializer(serializers.Serializer):
    """
    Validates the request payload for GET /api/sync/preview/<pk>/

    Returns a lightweight preview of what a sync would transfer without
    actually writing any data. date_from / date_to are optional filters.
    """

    date_from = serializers.DateField(required=False, allow_null=True)
    date_to   = serializers.DateField(required=False, allow_null=True)

    def validate(self, data: dict) -> dict:
        date_from = data.get("date_from")
        date_to   = data.get("date_to")
        today     = timezone.localdate()

        if date_from and date_to and date_from > date_to:
            raise serializers.ValidationError(
                {"date_to": "date_to must be on or after date_from."}
            )
        if date_from and date_from > today:
            raise serializers.ValidationError(
                {"date_from": "date_from cannot be in the future."}
            )
        if date_to and date_to > today:
            raise serializers.ValidationError(
                {"date_to": "date_to cannot be in the future."}
            )

        return data


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class SyncStatsSerializer(serializers.Serializer):
    """
    Output-only serializer for GET /api/sync/stats/

    Passed as a positional instance (never data=) so .data serializes
    directly from the aggregated dict without going through validation.
    """
    total_jobs      = serializers.IntegerField()
    pending_jobs    = serializers.IntegerField()
    running_jobs    = serializers.IntegerField()
    successful_jobs = serializers.IntegerField()
    failed_jobs     = serializers.IntegerField()
    cancelled_jobs  = serializers.IntegerField()

    total_records_pulled  = serializers.IntegerField()
    total_records_pushed  = serializers.IntegerField()
    total_records_skipped = serializers.IntegerField()

    avg_duration_secs = serializers.FloatField(allow_null=True)
    last_sync_at      = serializers.DateTimeField(allow_null=True)
    last_success_at   = serializers.DateTimeField(allow_null=True)
