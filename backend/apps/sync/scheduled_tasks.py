# apps/sync/scheduled_tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(name="sync.scheduled_sync_all_active")
def scheduled_sync_all_active():
    from apps.projects.models import SiteProject
    from apps.registry.models import CentralRegistry
    from apps.sync.models import SyncJob, SyncLog
    from apps.sync.tasks import run_sync_job

    registry = CentralRegistry.get_active()
    if not registry:
        logger.error("Scheduled sync: no active registry configured — skipping")
        return {"queued": 0, "skipped": 0, "reason": "No active registry"}

    active_projects = SiteProject.objects.filter(
        status="active"
    ).select_related("site")

    queued  = 0
    skipped = 0

    for project in active_projects:
        if not project.has_token():
            logger.warning("Scheduled sync: skipping %s — no active token", project)
            skipped += 1
            continue

        already_running = SyncJob.objects.filter(
            site_project = project,
            status__in   = ["pending", "running"],
        ).exists()

        if already_running:
            logger.info("Scheduled sync: skipping %s — job already in progress", project)
            skipped += 1
            continue

        job = SyncJob.objects.create(
            site_project = project,
            registry     = registry,
            sync_type    = "full",
            triggered_by = None,
        )
        SyncLog.write(job, "INFO", "Scheduled nightly sync — queued by system")

        task = run_sync_job.delay(job.pk)
        job.celery_task_id = task.id
        job.save(update_fields=["celery_task_id"])

        logger.info("Scheduled sync: queued job %s for %s (task=%s)",
                    job.pk, project, task.id)
        queued += 1

    logger.info("Scheduled sync complete — queued=%s skipped=%s", queued, skipped)
    return {"queued": queued, "skipped": skipped}