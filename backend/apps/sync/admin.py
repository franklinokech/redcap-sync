# apps/sync/admin.py
from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html

from .models import SyncJob, SyncLog


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Maps each SyncJob status value to a (background-colour, text-colour) pair
# that works in both light and dark Django admin themes.
_STATUS_COLOURS: dict[str, tuple[str, str]] = {
    SyncJob.Status.PENDING:   ("#f0ad4e", "#000"),   # amber
    SyncJob.Status.RUNNING:   ("#5bc0de", "#000"),   # blue
    SyncJob.Status.SUCCESS:   ("#5cb85c", "#fff"),   # green
    SyncJob.Status.FAILED:    ("#d9534f", "#fff"),   # red
    SyncJob.Status.CANCELLED: ("#aaa",    "#fff"),   # grey
}

_LOG_LEVEL_COLOURS: dict[str, tuple[str, str]] = {
    SyncLog.Level.DEBUG:   ("#ccc",    "#000"),
    SyncLog.Level.INFO:    ("#5bc0de", "#000"),
    SyncLog.Level.WARNING: ("#f0ad4e", "#000"),
    SyncLog.Level.ERROR:   ("#d9534f", "#fff"),
}


def _coloured_badge(value: str, colour_map: dict[str, tuple[str, str]]) -> str:
    """Return an HTML <span> badge for *value* using *colour_map*."""
    bg, fg = colour_map.get(value, ("#eee", "#000"))
    return format_html(
        '<span style="'
        "background:{bg};color:{fg};"
        "padding:2px 8px;border-radius:4px;"
        'font-size:0.85em;font-weight:600;">'
        "{label}</span>",
        bg=bg,
        fg=fg,
        label=value,
    )


# ---------------------------------------------------------------------------
# Inline
# ---------------------------------------------------------------------------


class SyncLogInline(admin.TabularInline):
    """
    Read-only inline showing log entries for a SyncJob.

    Logs are immutable audit records and must not be created, edited, or
    deleted through the admin interface.
    """

    model = SyncLog
    extra = 0
    can_delete = False
    show_change_link = True          # lets staff navigate to the full log row
    ordering = ["timestamp"]
    readonly_fields = ["timestamp", "level", "message", "detail"]

    def has_add_permission(self, request, obj=None) -> bool:  # type: ignore[override]
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False


# ---------------------------------------------------------------------------
# SyncJob admin
# ---------------------------------------------------------------------------


@admin.register(SyncJob)
class SyncJobAdmin(admin.ModelAdmin):
    # ── List view ────────────────────────────────────────────────────────────
    list_display = [
        "id",
        "site_project",
        "registry",
        "sync_type",
        "status_badge",      # coloured badge replaces raw status string
        "date_from",
        "date_to",
        "records_pulled",
        "records_pushed",
        "records_skipped",
        "duration_secs",
        "triggered_by",
        "created_at",
    ]
    list_filter  = ["status", "sync_type", "site_project__site", "registry"]
    search_fields = [
        "site_project__name",
        "registry__name",
        "celery_task_id",
        "triggered_by__username",
    ]
    ordering              = ["-created_at"]
    date_hierarchy        = "created_at"
    show_full_result_count = False

    # Pre-fetch FK data to avoid N+1 queries in list_display
    list_select_related = ["site_project__site", "registry", "triggered_by"]

    # ── Detail view ──────────────────────────────────────────────────────────
    # Fields set by the Celery task or at creation time must never be edited.
    readonly_fields = [
        # Identity / tracing
        "celery_task_id",
        # Audit snapshots — frozen at job-creation time
        "forms_snapshot",
        "fields_snapshot",
        # Task-managed state
        "status",
        "records_pulled",
        "records_pushed",
        "records_skipped",
        "duration_secs",
        "error_message",
        # Timestamps — all managed automatically
        "created_at",
        "started_at",
        "completed_at",
    ]

    # raw_id_fields falls back to a plain integer widget; autocomplete_fields
    # shows a searchable dropdown — requires search_fields on the target admin.
    raw_id_fields = ["triggered_by"]
    autocomplete_fields = ["site_project", "registry"]

    inlines = [SyncLogInline]

    fieldsets = [
        (
            "Job identity",
            {
                "fields": [
                    "site_project",
                    "registry",
                    "triggered_by",
                    "celery_task_id",
                ]
            },
        ),
        (
            "Sync scope",
            {
                "fields": [
                    "sync_type",
                    "date_from",
                    "date_to",
                    "forms_snapshot",
                    "fields_snapshot",
                ]
            },
        ),
        (
            "Status & results",
            {
                "fields": [
                    "status",
                    "records_pulled",
                    "records_pushed",
                    "records_skipped",
                    "duration_secs",
                    "error_message",
                ]
            },
        ),
        (
            "Timestamps",
            {
                "fields": ["created_at", "started_at", "completed_at"],
                "classes": ["collapse"],
            },
        ),
    ]

    # ── Custom list columns ──────────────────────────────────────────────────

    @admin.display(description="Status", ordering="status")
    def status_badge(self, obj: SyncJob) -> str:
        return _coloured_badge(obj.status, _STATUS_COLOURS)

    # ── Permission overrides ─────────────────────────────────────────────────

    def has_add_permission(self, request) -> bool:
        """
        Jobs must only be created via the API (TriggerSyncView / RetryFailedSyncView).
        Blocking admin creation prevents bypassing the 409 duplicate-job guard.
        """
        return False

    def has_delete_permission(self, request, obj: SyncJob | None = None) -> bool:
        """
        Prevent deletion of PENDING or RUNNING jobs — deleting an active job
        would leave the Celery task orphaned with no job record to update.
        """
        if obj is not None and obj.status in (
            SyncJob.Status.PENDING,
            SyncJob.Status.RUNNING,
        ):
            return False
        return request.user.is_superuser


# ---------------------------------------------------------------------------
# SyncLog admin
# ---------------------------------------------------------------------------


@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    # ── List view ────────────────────────────────────────────────────────────
    list_display = ["id", "job_link", "level_badge", "message", "timestamp"]
    list_filter  = ["level", "job__status"]
    search_fields = [
        "message",
        "job__id",
        "job__site_project__name",
        "job__celery_task_id",
    ]
    ordering               = ["-timestamp"]
    date_hierarchy         = "timestamp"
    show_full_result_count = False
    list_select_related    = ["job__site_project__site"]

    # ── Detail view ──────────────────────────────────────────────────────────
    # Every field is read-only: logs are append-only audit records.
    readonly_fields = ["job", "level", "message", "detail", "timestamp"]

    # ── Permission overrides: logs are fully immutable ───────────────────────

    def has_add_permission(self, request) -> bool:
        return False

    def has_change_permission(self, request, obj=None) -> bool:
        return False

    def has_delete_permission(self, request, obj=None) -> bool:
        """
        Only superusers may delete log entries (e.g. GDPR/data-hygiene tasks).
        Regular staff cannot delete logs.
        """
        return request.user.is_superuser

    # ── Custom list columns ──────────────────────────────────────────────────

    @admin.display(description="Job", ordering="job__id")
    def job_link(self, obj: SyncLog) -> str:
        """Clickable link to the parent SyncJob change page."""
        from django.urls import reverse  # noqa: PLC0415

        url = reverse("admin:sync_syncjob_change", args=[obj.job_id])
        return format_html('<a href="{}">#{}  {}</a>', url, obj.job_id, obj.job)

    @admin.display(description="Level", ordering="level")
    def level_badge(self, obj: SyncLog) -> str:
        return _coloured_badge(obj.level, _LOG_LEVEL_COLOURS)
