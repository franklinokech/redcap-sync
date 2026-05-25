# config/celery.py
import os

from celery import Celery
from celery.schedules import crontab

# ---------------------------------------------------------------------------
# Django settings resolution
# ---------------------------------------------------------------------------
# Override this environment variable in production:
#   export DJANGO_SETTINGS_MODULE=config.settings.prod
# ---------------------------------------------------------------------------
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")

app = Celery("redcap_sync")

# Celery reads every Django setting prefixed with CELERY_
app.config_from_object("django.conf:settings", namespace="CELERY")

# Automatically discover tasks in installed apps (looks for tasks.py)
app.autodiscover_tasks()

# ---------------------------------------------------------------------------
# Security hardening
# ---------------------------------------------------------------------------
app.conf.update(
    # Never use pickle; JSON is safe and human-readable
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Reject tasks that have been waiting too long (prevents stale execution)
    task_reject_on_worker_lost=True,
    # Acknowledge the task only after it completes, not on receipt.
    # Combined with reject_on_worker_lost this means a task is re-queued
    # if the worker crashes mid-execution.
    task_acks_late=True,
)

# ---------------------------------------------------------------------------
# Timezone
# ---------------------------------------------------------------------------
# All beat schedule times are interpreted in this timezone.
# Must match TIME_ZONE in Django settings.
app.conf.timezone = "Africa/Nairobi"
app.conf.enable_utc = True  # Store timestamps in UTC internally

# ---------------------------------------------------------------------------
# Beat schedule
# ---------------------------------------------------------------------------
app.conf.beat_schedule = {
    # Nightly full sync for all active SiteProjects
    # Runs at 01:00 Africa/Nairobi every day.
    # Choose a low-traffic window appropriate for your environment.
    "scheduled-sync-all-active": {
        "task": "sync.scheduled_sync_all_active",
        "schedule": crontab(hour=1, minute=0),
        "options": {
            # Route to the dedicated beat queue so it does not compete
            # with user-triggered syncs on the default queue.
            "queue": "beat",
        },
    },
}


# ---------------------------------------------------------------------------
# Debug task (development only)
# ---------------------------------------------------------------------------
@app.task(bind=True, ignore_result=True)
def debug_task(self):
    # Use the standard logger inside the task, not at module level
    from celery.utils.log import get_task_logger  # noqa: PLC0415

    logger = get_task_logger(__name__)
    logger.info("Debug task request: %r", self.request)
