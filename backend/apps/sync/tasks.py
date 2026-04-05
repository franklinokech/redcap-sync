# apps/sync/tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=600,
    time_limit=660,
    name="sync.run_sync_job",
)
def run_sync_job(self, job_id: int):
    from apps.sync.models import SyncJob, SyncLog
    from core.r_client import RServiceClient
    from celery.exceptions import SoftTimeLimitExceeded

    try:
        job = SyncJob.objects.select_related(
            "site_project", "site_project__site",
            "registry", "triggered_by"
        ).get(pk=job_id)
    except SyncJob.DoesNotExist:
        logger.error("SyncJob %s not found — aborting task", job_id)
        return

    logger.info("Starting sync job %s — %s", job_id, job.site_project)

    job.mark_running()
    SyncLog.write(job, "INFO", f"Task picked up by worker (task_id={self.request.id})")

    try:
        source_token   = job.site_project.get_active_token_plaintext()
        registry_token = job.registry.get_token()

        client = RServiceClient()

        SyncLog.write(job, "INFO",
            f"Calling R sync service — {job.get_sync_type_display()}"
        )

        result = client.sync(
            source_token          = source_token,
            source_url            = job.site_project.redcap_url,
            registry_token        = registry_token,
            registry_url          = job.registry.redcap_url,
            sync_type             = job.sync_type,
            date_from             = str(job.date_from) if job.date_from else None,
            date_to               = str(job.date_to)   if job.date_to   else None,
            forms                 = job.site_project.get_sync_forms_list(),
            fields                = job.site_project.get_sync_fields_list(),
            overwrite_with_blanks = job.registry.overwrite_with_blanks,
            record_id_prefix      = job.site_project.record_id_prefix or None,
        )

        if result.get("success"):
            def unwrap(val):
                return val[0] if isinstance(val, list) else val

            records_pulled = unwrap(result.get("records_pulled", 0))
            records_pushed = unwrap(result.get("records_pushed", 0))
            duration       = unwrap(result.get("duration_secs",  0))

            job.mark_success(
                records_pulled = records_pulled,
                records_pushed = records_pushed,
                duration_secs  = duration,
            )
            SyncLog.write(
                job, "INFO",
                f"Sync complete — pulled {records_pulled}, pushed {records_pushed} records in {duration}s",
                detail=result,
            )
            logger.info("Job %s succeeded — %s records pushed", job_id, records_pushed)

        else:
            error = result.get("message", "Unknown error from R service")
            if isinstance(error, list):
                error = error[0]
            job.mark_failed(error)
            SyncLog.write(job, "ERROR", error, detail=result)
            logger.error("Job %s failed — %s", job_id, error)

    except SoftTimeLimitExceeded:
        msg = f"Job {job_id} exceeded the 10 minute time limit and was terminated."
        logger.error(msg)
        job.mark_failed(msg)
        SyncLog.write(job, "ERROR", msg)

    except ConnectionError as exc:
        msg = str(exc)
        logger.warning("Job %s — connection error, retrying: %s", job_id, msg)
        SyncLog.write(job, "WARNING", f"Connection error — retrying ({self.request.retries + 1}/3): {msg}")

        job.status = SyncJob.Status.PENDING
        job.save(update_fields=["status"])

        raise self.retry(exc=exc)

    except Exception as exc:
        msg = str(exc)
        logger.exception("Job %s — unexpected error: %s", job_id, msg)
        job.mark_failed(msg)
        SyncLog.write(job, "ERROR", f"Unexpected error: {msg}")