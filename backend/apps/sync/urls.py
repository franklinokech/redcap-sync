# apps/sync/urls.py
"""
URL configuration for the sync application.

Endpoints are grouped into three logical sections:

  Project-scoped actions
  ──────────────────────
  POST  /api/sync/trigger/<pk>/   — create and enqueue a SyncJob
  POST  /api/sync/preview/<pk>/   — dry-run preview via the R service

  Job collection (read-only, paginated)
  ──────────────────────────────────────
  GET   /api/sync/jobs/            — list all accessible jobs

  Job instance actions
  ────────────────────
  GET   /api/sync/jobs/<pk>/       — full job detail with nested logs
  GET   /api/sync/jobs/<pk>/logs/  — log entries for a single job
  POST  /api/sync/jobs/<pk>/cancel/ — cancel PENDING or RUNNING job
  POST  /api/sync/jobs/<pk>/retry/  — re-queue FAILED or CANCELLED job

  Aggregates
  ──────────
  GET   /api/sync/stats/           — aggregate metrics across accessible jobs

All endpoints require a valid JWT (IsAuthenticated).
Staff/superusers see all jobs; regular users see only jobs for their site.
"""

from django.urls import path

from . import views
from .views import (
    CancelSyncView,
    PreviewSyncView,
    RetryFailedSyncView,
    SyncJobDetailView,
    SyncJobListView,
    SyncJobLogsView,
    SyncStatsView,
    TriggerSyncView,
)

app_name = "sync"

urlpatterns = [
    path('r-health/', views.r_health, name='sync-r-health'),
    # ── Project-scoped actions ───────────────────────────────────────────────
    # pk = SiteProject.pk
    path("trigger/<int:pk>/",  TriggerSyncView.as_view(), name="trigger"),
    path("preview/<int:pk>/",  PreviewSyncView.as_view(), name="preview"),

    # ── Job collection (GET only — SyncJobListView is a read-only ListAPIView) ─
    path("jobs/",              SyncJobListView.as_view(), name="job-list"),

    # ── Job instance actions ─────────────────────────────────────────────────
    # pk = SyncJob.pk for all routes below
    path("jobs/<int:pk>/",         SyncJobDetailView.as_view(),   name="job-detail"),
    path("jobs/<int:pk>/logs/",    SyncJobLogsView.as_view(),     name="job-logs"),
    path("jobs/<int:pk>/cancel/",  CancelSyncView.as_view(),      name="job-cancel"),
    path("jobs/<int:pk>/retry/",   RetryFailedSyncView.as_view(), name="job-retry"),

    # ── Aggregates ───────────────────────────────────────────────────────────
    path("stats/",             SyncStatsView.as_view(),    name="stats"),
]
