# apps/sync/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone


class SyncJob(models.Model):
    """
    One sync run: pulls records from a SiteProject and pushes to the CentralRegistry.

    A user can trigger a sync for any project they have access to.
    Multiple jobs can run concurrently for different projects.
    Jobs are executed asynchronously via Celery.

    Lifecycle:
        created → PENDING → RUNNING → SUCCESS | FAILED | CANCELLED
    """

    class Status(models.TextChoices):
        PENDING   = "pending",   "Pending"
        RUNNING   = "running",   "Running"
        SUCCESS   = "success",   "Success"
        FAILED    = "failed",    "Failed"
        CANCELLED = "cancelled", "Cancelled"

    class SyncType(models.TextChoices):
        FULL    = "full",    "Full Sync"
        PARTIAL = "partial", "Partial (Date Range)"

    # ── What is being synced ──────────────────────────────────────────────────

    site_project = models.ForeignKey(
        "projects.SiteProject",
        on_delete=models.CASCADE,
        related_name="sync_jobs",
        help_text="The source project being synced",
    )
    registry = models.ForeignKey(
        "registry.CentralRegistry",
        on_delete=models.CASCADE,
        related_name="sync_jobs",
        help_text="The target registry receiving the data",
    )

    # ── Sync parameters ───────────────────────────────────────────────────────

    sync_type = models.CharField(
        max_length=10,
        choices=SyncType.choices,
        default=SyncType.FULL,
    )
    date_from = models.DateField(
        null=True,
        blank=True,
        help_text="Inclusive start date (only for partial sync)",
    )
    date_to = models.DateField(
        null=True,
        blank=True,
        help_text="Inclusive end date (only for partial sync)",
    )

    # Snapshot the form/field scoping at the time of the job
    # (in case the project config changes after the job runs)
    forms_snapshot  = models.TextField(blank=True, help_text="Comma-separated forms used for this job")
    fields_snapshot = models.TextField(blank=True, help_text="Comma-separated fields used for this job")

    # ── Execution state ───────────────────────────────────────────────────────

    status         = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    records_pulled = models.PositiveIntegerField(default=0)
    records_pushed = models.PositiveIntegerField(default=0)
    duration_secs  = models.FloatField(null=True, blank=True)
    error_message  = models.TextField(blank=True)

    # Celery task ID — used to check status or revoke a running job
    celery_task_id = models.CharField(max_length=255, blank=True)

    # ── Audit ─────────────────────────────────────────────────────────────────

    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="triggered_syncs",
    )
    started_at   = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = "sync_job"
        ordering            = ["-created_at"]
        verbose_name        = "Sync Job"
        verbose_name_plural = "Sync Jobs"
        indexes = [
            models.Index(fields=["status"],                    name="idx_syncjob_status"),
            models.Index(fields=["site_project", "status"],    name="idx_syncjob_project_status"),
            models.Index(fields=["site_project", "created_at"],name="idx_syncjob_project_date"),
            models.Index(fields=["created_at"],                name="idx_syncjob_created"),
        ]

    def __str__(self):
        return (
            f"Job #{self.pk} | {self.site_project} | "
            f"{self.get_sync_type_display()} | {self.get_status_display()}"
        )

    # ── State helpers ─────────────────────────────────────────────────────────

    @property
    def is_complete(self):
        return self.status in (
            self.Status.SUCCESS,
            self.Status.FAILED,
            self.Status.CANCELLED,
        )

    @property
    def date_range_display(self):
        if self.sync_type == self.SyncType.FULL:
            return "Full sync (all records)"
        parts = []
        if self.date_from:
            parts.append(str(self.date_from))
        if self.date_to:
            parts.append(str(self.date_to))
        return " → ".join(parts) if parts else "No date range set"

    def mark_running(self):
        self.status     = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_success(self, records_pulled, records_pushed, duration_secs):
        self.status         = self.Status.SUCCESS
        self.records_pulled = records_pulled
        self.records_pushed = records_pushed
        self.duration_secs  = duration_secs
        self.completed_at   = timezone.now()
        self.save(update_fields=[
            "status", "records_pulled", "records_pushed",
            "duration_secs", "completed_at",
        ])

    def mark_failed(self, error_message, duration_secs=None):
        self.status        = self.Status.FAILED
        self.error_message = error_message
        self.duration_secs = duration_secs
        self.completed_at  = timezone.now()
        self.save(update_fields=[
            "status", "error_message", "duration_secs", "completed_at",
        ])


class SyncLog(models.Model):
    """
    Individual log entry for a SyncJob.

    Written at each stage of the sync pipeline — validation, pull, push,
    completion. Provides a full audit trail for every sync run.

    The detail field stores structured JSON for machine-readable context
    (e.g. R service response body, record counts per batch).
    """

    class Level(models.TextChoices):
        DEBUG   = "DEBUG",   "Debug"
        INFO    = "INFO",    "Info"
        WARNING = "WARNING", "Warning"
        ERROR   = "ERROR",   "Error"

    job     = models.ForeignKey(
        SyncJob,
        on_delete=models.CASCADE,
        related_name="logs",
    )
    level   = models.CharField(max_length=10, choices=Level.choices, default=Level.INFO)
    message = models.TextField()
    detail  = models.JSONField(
        null=True,
        blank=True,
        help_text="Optional structured data — e.g. R service response, error traceback",
    )
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table            = "sync_log"
        ordering            = ["timestamp"]
        verbose_name        = "Sync Log"
        verbose_name_plural = "Sync Logs"
        indexes = [
            models.Index(fields=["job", "level"],  name="idx_synclog_job_level"),
            models.Index(fields=["job", "timestamp"], name="idx_synclog_job_time"),
        ]

    def __str__(self):
        return f"[{self.level}] {self.timestamp:%Y-%m-%d %H:%M:%S} — {self.message[:80]}"

    @classmethod
    def write(cls, job, level, message, detail=None):
        """Convenience shorthand: SyncLog.write(job, 'INFO', 'Pull started')"""
        return cls.objects.create(job=job, level=level, message=message, detail=detail)