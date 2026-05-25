# apps/sync/scheduled_tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(name="sync.scheduled_sync_all_active")
def scheduled_sync_all_active() -> dict:
    """
    Nightly scheduled task that queues a FULL sync for every active
    SiteProject that has a linked CentralRegistry and an active API token.

    Each project is responsible for its own registry assignment.  Projects
    without a registry link, without an active token, or with a job already
    in progress are skipped individually rather than aborting the whole run.

    Returns a summary dict: {"queued": int, "skipped": int, "errors": int}.
    """
    from apps.projects.models import SiteProject  # noqa: PLC0415
    from apps.sync.models import SyncJob, SyncLog  # noqa: PLC0415
    from apps.sync.tasks import run_sync_job  # noqa: PLC0415

    active_projects = (
        SiteProject.objects.filter(status=SiteProject.Status.ACTIVE)
        .select_related("site", "central_registry")
    )

    queued = 0
    skipped = 0
    errors = 0

    for project in active_projects:

        # -- Guard: registry must be linked -----------------------------------
        if not project.central_registry_id:
            logger.info(
                "Scheduled sync: skipping %s — no registry linked", project
            )
            skipped += 1
            continue

        # -- Guard: active API token required ---------------------------------
        if not project.has_token():
            logger.warning(
                "Scheduled sync: skipping %s — no active token", project
            )
            skipped += 1
            continue

        # -- Guard: no concurrent job -----------------------------------------
        already_running = SyncJob.objects.filter(
            site_project=project,
            status__in=[SyncJob.Status.PENDING, SyncJob.Status.RUNNING],
        ).exists()

        if already_running:
            logger.info(
                "Scheduled sync: skipping %s — job already in progress", project
            )
            skipped += 1
            continue

        # -- Create job with config snapshots ---------------------------------
        try:
            job = SyncJob.objects.create(
                site_project=project,
                registry=project.central_registry,
                sync_type=SyncJob.SyncType.FULL,
                triggered_by=None,
                # Snapshot current config so retries use a consistent scope
                forms_snapshot=project.sync_forms or "",
                fields_snapshot=project.sync_fields or "",
            )
        except Exception as exc:
            logger.exception(
                "Scheduled sync: failed to create job for %s — %s", project, exc
            )
            errors += 1
            continue

        SyncLog.write(
            job,
            SyncLog.Level.INFO,
            "Scheduled nightly sync — queued by system",
        )

        # -- Dispatch Celery task ---------------------------------------------
        try:
            task = run_sync_job.delay(job.pk)
            job.celery_task_id = task.id
            job.save(update_fields=["celery_task_id"])
        except Exception as exc:
            logger.exception(
                "Scheduled sync: failed to dispatch task for job %s — %s", job.pk, exc
            )
            job.mark_failed(f"Failed to dispatch Celery task: {exc}")
            SyncLog.write(
                job,
                SyncLog.Level.ERROR,
                f"Task dispatch failed — {exc}",
            )
            errors += 1
            continue

        logger.info(
            "Scheduled sync: queued job %s for %s (task=%s)",
            job.pk,
            project,
            task.id,
        )
        queued += 1

    logger.info(
        "Scheduled sync complete — queued=%s skipped=%s errors=%s",
        queued,
        skipped,
        errors,
    )
    return {"queued": queued, "skipped": skipped, "errors": errors}
