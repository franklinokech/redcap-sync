# apps/sync/models.py

from __future__ import annotations

from typing import Optional

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class SyncJob(models.Model):
    """
    One sync run: pulls records from a SiteProject and pushes to the CentralRegistry.

    Lifecycle:
        created -> PENDING -> RUNNING -> SUCCESS | FAILED | CANCELLED

    Jobs are executed asynchronously via Celery.
    Multiple jobs can run concurrently for different projects.
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

    # -- What is being synced ------------------------------------------------

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

    # -- Sync parameters -----------------------------------------------------

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

    # Snapshot the form/field scoping at the time of the job so that config
    # changes after job creation do not retroactively alter the audit trail.
    forms_snapshot = models.TextField(
        blank=True,
        help_text="Comma-separated forms used for this job",
    )
    fields_snapshot = models.TextField(
        blank=True,
        help_text="Comma-separated fields used for this job",
    )

    # -- Execution state -----------------------------------------------------

    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    records_pulled  = models.PositiveIntegerField(default=0)
    records_pushed  = models.PositiveIntegerField(default=0)
    records_skipped = models.PositiveIntegerField(default=0)
    duration_secs   = models.FloatField(null=True, blank=True)
    error_message   = models.TextField(blank=True)

    # Celery task ID — used to check status or revoke a running job via Celery inspect
    celery_task_id = models.CharField(max_length=255, blank=True, db_index=True)

    # -- Audit ---------------------------------------------------------------

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
            models.Index(fields=["status"],                     name="idx_syncjob_status"),
            models.Index(fields=["site_project", "status"],     name="idx_syncjob_project_status"),
            models.Index(fields=["site_project", "created_at"], name="idx_syncjob_project_date"),
            models.Index(fields=["registry", "status"],         name="idx_syncjob_registry_status"),
            models.Index(fields=["created_at"],                 name="idx_syncjob_created"),
            # celery_task_id uses db_index=True on the field itself (single-column)
        ]

    def __str__(self) -> str:
        return (
            f"Job #{self.pk} | {self.site_project} | "
            f"{self.get_sync_type_display()} | {self.get_status_display()}"
        )

    # -- Model-level validation ----------------------------------------------

    def clean(self) -> None:
        """Validate partial-sync date range at the model level."""
        if self.sync_type == self.SyncType.PARTIAL:
            if not self.date_from and not self.date_to:
                raise ValidationError(
                    "A partial sync requires at least one of date_from or date_to."
                )
            if self.date_from and self.date_to and self.date_from > self.date_to:
                raise ValidationError(
                    {"date_to": "date_to must be on or after date_from."}
                )
        if self.sync_type == self.SyncType.FULL:
            if self.date_from or self.date_to:
                raise ValidationError(
                    "date_from / date_to are only used with partial sync. "
                    "Clear them or switch sync_type to 'partial'."
                )

    # -- State helpers -------------------------------------------------------

    @property
    def is_complete(self) -> bool:
        """True when the job has reached a terminal state."""
        return self.status in (
            self.Status.SUCCESS,
            self.Status.FAILED,
            self.Status.CANCELLED,
        )

    @property
    def is_cancellable(self) -> bool:
        """True while the job can still be stopped."""
        return self.status in (self.Status.PENDING, self.Status.RUNNING)

    @property
    def date_range_display(self) -> str:
        if self.sync_type == self.SyncType.FULL:
            return "Full sync (all records)"
        parts = []
        if self.date_from:
            parts.append(str(self.date_from))
        if self.date_to:
            parts.append(str(self.date_to))
        return " - ".join(parts) if parts else "No date range set"

    @property
    def summary(self) -> dict:
        """
        Machine-readable summary for API responses and Celery task results.

        error_message is included so callers do not need a second query when
        polling a failed job.
        """
        return {
            "status":          self.status,
            "records_pulled":  self.records_pulled,
            "records_pushed":  self.records_pushed,
            "records_skipped": self.records_skipped,
            "duration_secs":   self.duration_secs,
            "error_message":   self.error_message or None,  # normalise "" -> None
            "started_at":      self.started_at,
            "completed_at":    self.completed_at,
        }

    # -- State transitions ---------------------------------------------------

    def mark_running(self) -> None:
        """
        Transition PENDING -> RUNNING.

        Guard prevents accidentally restarting a job that has already
        completed or is already running.
        """
        if self.is_complete:
            raise ValueError(
                f"Cannot mark job #{self.pk} as running — "
                f"it is already in a terminal state ({self.status})."
            )
        if self.status == self.Status.RUNNING:
            return  # idempotent — Celery may call this twice on retry
        self.status     = self.Status.RUNNING
        self.started_at = timezone.now()
        self.save(update_fields=["status", "started_at"])

    def mark_success(
        self,
        records_pulled:  int,
        records_pushed:  int,
        duration_secs:   float,
        records_skipped: int = 0,
    ) -> None:
        self.status          = self.Status.SUCCESS
        self.records_pulled  = records_pulled
        self.records_pushed  = records_pushed
        self.records_skipped = records_skipped
        self.duration_secs   = duration_secs
        self.completed_at    = timezone.now()
        self.save(update_fields=[
            "status", "records_pulled", "records_pushed",
            "records_skipped", "duration_secs", "completed_at",
        ])

    def mark_failed(
        self,
        error_message:  str,
        duration_secs:  Optional[float] = None,
        records_pulled: int = 0,
        records_pushed: int = 0,
    ) -> None:
        self.status         = self.Status.FAILED
        self.error_message  = error_message
        self.duration_secs  = duration_secs
        self.records_pulled = records_pulled
        self.records_pushed = records_pushed
        self.completed_at   = timezone.now()
        self.save(update_fields=[
            "status", "error_message", "duration_secs",
            "records_pulled", "records_pushed", "completed_at",
        ])

    def mark_cancelled(self, reason: str = "") -> None:
        """
        Transition to CANCELLED.

        Safe to call even if the job never started (PENDING).
        Idempotent — no-op if the job is already in a terminal state.
        """
        if self.is_complete:
            return
        self.status        = self.Status.CANCELLED
        self.error_message = reason or "Cancelled by user"
        self.completed_at  = timezone.now()
        self.save(update_fields=["status", "error_message", "completed_at"])


# ---------------------------------------------------------------------------


class SyncLog(models.Model):
    """
    Individual log entry for a SyncJob.

    Written at each stage of the sync pipeline (validation, pull, push,
    completion). Provides a full audit trail for every sync run.

    The ``detail`` field stores structured JSON for machine-readable context
    (e.g. R service response body, record counts per batch).
    """

    class Level(models.TextChoices):
        DEBUG   = "DEBUG",   "Debug"
        INFO    = "INFO",    "Info"
        WARNING = "WARNING", "Warning"
        ERROR   = "ERROR",   "Error"

    job = models.ForeignKey(
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
            models.Index(fields=["job", "level"],     name="idx_synclog_job_level"),
            models.Index(fields=["job", "timestamp"], name="idx_synclog_job_time"),
        ]

    def __str__(self) -> str:
        return f"[{self.level}] {self.timestamp:%Y-%m-%d %H:%M:%S} — {self.message[:80]}"

    # -- Convenience writers -------------------------------------------------

    @classmethod
    def write(
        cls,
        job:     SyncJob,
        level:   str,
        message: str,
        detail:  object = None,
    ) -> "SyncLog":
        """Single-entry shorthand::

            SyncLog.write(job, "INFO", "Pull started")
        """
        return cls.objects.create(job=job, level=level, message=message, detail=detail)

    @classmethod
    def write_bulk(
        cls,
        job:     SyncJob,
        entries: list[tuple[str, str, object]],
    ) -> None:
        """
        Insert multiple log entries in one DB round-trip::

            SyncLog.write_bulk(job, [
                ("INFO",    "Pull complete",       {"count": 42}),
                ("WARNING", "2 records skipped",   None),
            ])
        """
        cls.objects.bulk_create([
            cls(job=job, level=level, message=msg, detail=detail)
            for level, msg, detail in entries
        ])
