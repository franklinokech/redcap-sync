# apps/sync/tasks.py
from __future__ import annotations

import json
import logging

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_client():
    """Build RServiceClient from Django settings."""
    from django.conf import settings
    from core.r_client import RServiceClient

    return RServiceClient(
        base_url=getattr(settings, "R_SYNC_SERVICE_URL",    "http://localhost:8000"),
        api_key =getattr(settings, "R_SYNC_SERVICE_API_KEY", ""),
        timeout =float(getattr(settings, "R_SYNC_SERVICE_TIMEOUT", 300)),
    )


def _split_snapshot(snapshot: str) -> list[str]:
    """
    Parse a forms/fields snapshot stored as JSON list or comma-separated CSV.
    Returns an empty list for blank/null values.
    """
    if not snapshot:
        return []
    snapshot = snapshot.strip()
    if snapshot.startswith("["):
        try:
            parsed = json.loads(snapshot)
            return [str(x).strip() for x in parsed if str(x).strip()]
        except (json.JSONDecodeError, TypeError):
            pass
    return [x.strip() for x in snapshot.split(",") if x.strip()]


def _decrypt_project_token(site_project) -> str:
    """
    Retrieve and decrypt the active APIToken for a SiteProject.

    The APIToken model stores the ciphertext in the field named ``token``
    and exposes ``get_plaintext()`` for decryption.

    Raises ValueError with a descriptive message on any failure.
    """
    token_obj = site_project.get_active_token()  # returns APIToken | None

    if token_obj is None:
        raise ValueError(
            f"No active API token found for SiteProject '{site_project}'."
        )

    if not token_obj.token:
        raise ValueError(
            f"APIToken (pk={token_obj.pk}) has an empty 'token' field "
            f"for SiteProject '{site_project}'."
        )

    try:
        plaintext = token_obj.get_plaintext()
    except ValueError as exc:
        raise ValueError(
            f"Token decryption failed for SiteProject '{site_project}' "
            f"(APIToken pk={token_obj.pk}): {exc}"
        ) from exc

    if not plaintext:
        raise ValueError(
            f"Decrypted token is empty for SiteProject '{site_project}'."
        )

    return plaintext


def _decrypt_registry_token(registry) -> str:
    """
    Decrypt the API token stored directly on the CentralRegistry instance.

    CentralRegistry stores its own Fernet-encrypted token via encrypted_token
    field and exposes it through get_token(). There is no separate APIToken
    model for registries.
    """
    if not registry.has_token:
        raise ValueError(
            f"CentralRegistry '{registry}' has no token stored. "
            f"Add one via Admin → Central Registries → {registry.pk}."
        )
    return registry.get_token()


def _check_sync_readiness(site_project) -> str:
    """
    Return a human-readable skip reason, or empty string if ready to sync.
    Mirrors the token checks actually used at runtime so the scheduler
    and the task agree on what "ready" means.
    """
    if not site_project.has_token:
        return "no active API token"

    registry = getattr(site_project, "central_registry", None)
    if not registry:
        return "no linked CentralRegistry"

    # Use the same helper the task uses — avoids duplicating logic
    if not registry.has_token:
        return "CentralRegistry has no token stored"

    if not getattr(site_project, "redcap_url", None):
        return "SiteProject has no redcap_url configured"

    if not getattr(registry, "redcap_url", None):
        return "CentralRegistry has no redcap_url configured"

    return ""


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_sync_job(self, job_id: int) -> dict:
    """
    Execute a single SyncJob identified by *job_id*.

    State machine:  pending → running → success | failed
    """
    from apps.sync.models import SyncJob, SyncLog

    # ------------------------------------------------------------------
    # 1. Load job + related objects in one query
    # ------------------------------------------------------------------
    try:
        job = (
            SyncJob.objects
            .select_related(
                "site_project",
                "site_project__site",
                "site_project__central_registry",
            )
            .get(pk=job_id)
        )
    except SyncJob.DoesNotExist:
        logger.error("SyncJob %s not found.", job_id)
        return {"error": f"SyncJob {job_id} not found"}

    site_project = job.site_project

    # ------------------------------------------------------------------
    # 2. Transition to RUNNING
    # ------------------------------------------------------------------
    try:
        job.mark_running()
    except Exception as exc:
        logger.warning("Could not mark job %s as running: %s", job_id, exc)

    SyncLog.objects.create(
        job=job,
        level=SyncLog.Level.INFO,
        message=f"Sync job {job_id} started (type={job.sync_type}).",
    )

    # Record wall-clock start so we can compute duration_secs ourselves.
    # timezone.now() is used throughout to stay tz-aware.
    import time as _time
    _wall_start = _time.monotonic()

    try:
        # --------------------------------------------------------------
        # 3. Decrypt source token  (field: APIToken.token)
        # --------------------------------------------------------------
        source_token = _decrypt_project_token(site_project)

        logger.debug(
            "Source token for job %s: length=%s alnum=%s",
            job_id, len(source_token), source_token.isalnum(),
        )

        # --------------------------------------------------------------
        # 4. Decrypt target (central registry) token
        # --------------------------------------------------------------
        registry = site_project.central_registry

        if not registry:
            raise ValueError(
                f"SiteProject '{site_project}' is not linked to a CentralRegistry."
            )

        target_token = _decrypt_registry_token(registry)

        logger.debug(
            "Target token for job %s: length=%s alnum=%s",
            job_id, len(target_token), target_token.isalnum(),
        )

        # --------------------------------------------------------------
        # 5. Validate URLs
        # --------------------------------------------------------------
        source_redcap_url = getattr(site_project, "redcap_url", "") or ""
        target_redcap_url = getattr(registry,      "redcap_url", "") or ""

        if not source_redcap_url:
            raise ValueError(
                f"SiteProject '{site_project}' has no redcap_url configured."
            )
        if not target_redcap_url:
            raise ValueError(
                f"CentralRegistry '{registry}' has no redcap_url configured."
            )

        # --------------------------------------------------------------
        # 6. Build R service payload
        # --------------------------------------------------------------
        forms  = _split_snapshot(job.forms_snapshot  or "")
        fields = _split_snapshot(job.fields_snapshot or "")

        payload: dict = {
            "token":             source_token,
            "redcap_url":        source_redcap_url,
            "target_token":      target_token,
            "target_redcap_url": target_redcap_url,
            "record_id_prefix":  getattr(site_project, "record_id_prefix", "") or "",
        }
        if forms:
            payload["forms"] = forms
        if fields:
            payload["fields"] = fields

        # BUG WAS HERE: SyncJob.partial / SyncJob.full do not exist.
        # Correct reference is SyncJob.SyncType.PARTIAL / .FULL
        # The stored DB value is the lowercase string "partial" / "full".
        if job.sync_type == SyncJob.SyncType.PARTIAL:
            if job.date_from:
                payload["date_from"] = job.date_from.isoformat()
            if job.date_to:
                payload["date_to"] = job.date_to.isoformat()

        # --------------------------------------------------------------
        # 7. Call R service
        # --------------------------------------------------------------
        SyncLog.objects.create(
            job=job,
            level=SyncLog.Level.INFO,
            message="Calling R sync service.",
            detail={
                "source_url":  source_redcap_url,
                "target_url":  target_redcap_url,
                "sync_type":   job.sync_type,
                "forms_count": len(forms),
                "fields_count": len(fields),
            },
        )

        with _make_client() as client:
            result = client.sync(**payload)

        records_pulled  = int(result.get("records_pulled",  0))
        records_pushed  = int(result.get("records_pushed",  0))
        records_skipped = int(result.get("records_skipped", 0))

        duration_secs = round(_time.monotonic() - _wall_start, 3)

        SyncLog.objects.create(
            job=job,
            level=SyncLog.Level.INFO,
            message=(
                f"Sync complete: pulled={records_pulled} "
                f"pushed={records_pushed} "
                f"skipped={records_skipped} "
                f"duration={duration_secs}s"
            ),
            detail={
                "records_pulled":  records_pulled,
                "records_pushed":  records_pushed,
                "records_skipped": records_skipped,
                "duration_secs":   duration_secs,
            },
        )

        # --------------------------------------------------------------
        # 8. Mark success  — duration_secs is a required arg
        # --------------------------------------------------------------
        job.mark_success(
            records_pulled=records_pulled,
            records_pushed=records_pushed,
            records_skipped=records_skipped,
            duration_secs=duration_secs,
        )

        return {
            "job_id":          job_id,
            "records_pulled":  records_pulled,
            "records_pushed":  records_pushed,
            "records_skipped": records_skipped,
            "duration_secs":   duration_secs,
        }

    except Exception as exc:
        duration_secs = round(_time.monotonic() - _wall_start, 3)
        error_msg = str(exc)
        logger.error("Sync job %s failed: %s", job_id, error_msg, exc_info=True)

        SyncLog.objects.create(
            job=job,
            level=SyncLog.Level.ERROR,
            message=f"Sync job {job_id} failed: {error_msg}",
            detail={"duration_secs": duration_secs},
        )
        job.mark_failed(
            error_message=error_msg,
            duration_secs=duration_secs,
        )

        # ---- Do NOT retry configuration errors ----
        _no_retry_phrases = (
            "decryption failed",
            "No active API token",
            "no active API token",
            "not linked to a CentralRegistry",
            "no redcap_url",
            "empty 'token' field",
            "no token storage",
            "Decrypted token is empty",
            "has no token stored",
        )
        if any(phrase in error_msg for phrase in _no_retry_phrases):
            logger.info(
                "Job %s: configuration error — not retrying. Reason: %s",
                job_id, error_msg,
            )
            return {"error": error_msg}

        # ---- Retry transient R-service / network errors ----
        raise self.retry(exc=exc)


# ---------------------------------------------------------------------------

@shared_task
def scheduled_sync_all_active() -> dict:
    """
    Nightly FULL sync for every active SiteProject that passes readiness checks.
    Intended to run at 02:00 UTC via django-celery-beat.
    """
    from apps.sync.models import SyncJob
    from apps.projects.models import SiteProject

    triggered: list[int]  = []
    skipped:   list[dict] = []

    projects = (
        SiteProject.objects
        .filter(status=SiteProject.Status.ACTIVE)
        .select_related("central_registry")
    )

    for sp in projects:
        reason = _check_sync_readiness(sp)
        if reason:
            skipped.append({"project_id": sp.pk, "reason": reason})
            logger.info(
                "Skipping scheduled sync for project %s (%s): %s",
                sp.pk, sp, reason,
            )
            continue

        # Skip if a job is already active for this project
        # BUG WAS HERE: SyncJob.pending / SyncJob.running do not exist.
        # Correct reference is SyncJob.Status.PENDING / .RUNNING
        already_active = SyncJob.objects.filter(
            site_project=sp,
            status__in=[
                SyncJob.Status.PENDING,
                SyncJob.Status.RUNNING,
            ],
        ).exists()

        if already_active:
            skipped.append({"project_id": sp.pk, "reason": "job already active"})
            logger.info(
                "Skipping scheduled sync for project %s: job already active.", sp.pk
            )
            continue

        # Snapshot forms/fields at dispatch time so the job is self-contained
        # BUG WAS HERE: SyncJob.full does not exist.
        # Correct reference is SyncJob.SyncType.FULL
        # triggered_by is a ForeignKey, cannot receive the string "scheduler"
        job = SyncJob.objects.create(
            site_project    = sp,
            registry        = sp.central_registry,
            sync_type       = SyncJob.SyncType.FULL,
            triggered_by    = None,                          # scheduler has no User
            forms_snapshot  = getattr(sp, "sync_forms",  "") or "",
            fields_snapshot = getattr(sp, "sync_fields", "") or "",
        )
        run_sync_job.delay(job.pk)
        triggered.append(job.pk)

        logger.info(
            "Scheduled FULL sync queued: job_id=%s project=%s (%s)",
            job.pk, sp.pk, sp,
        )

    logger.info(
        "scheduled_sync_all_active complete: triggered=%s skipped=%s",
        len(triggered), len(skipped),
    )
    return {"triggered": triggered, "skipped": skipped}
