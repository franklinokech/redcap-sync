# apps/sync/urls.py
from django.urls import path
from .views import (
    TriggerSyncView,
    PreviewSyncView,
    CancelSyncView,
    SyncJobListView,
    SyncJobDetailView,
    SyncJobLogsView,
    SyncStatsView,
)

urlpatterns = [
    path("trigger/",                TriggerSyncView.as_view(),   name="sync-trigger"),
    path("preview/",                PreviewSyncView.as_view(),   name="sync-preview"),
    path("jobs/",                   SyncJobListView.as_view(),   name="sync-job-list"),
    path("jobs/<int:pk>/",          SyncJobDetailView.as_view(), name="sync-job-detail"),
    path("jobs/<int:pk>/logs/",     SyncJobLogsView.as_view(),   name="sync-job-logs"),
    path("jobs/<int:pk>/cancel/",   CancelSyncView.as_view(),    name="sync-job-cancel"),
    path("stats/",                  SyncStatsView.as_view(),     name="sync-stats"),
]