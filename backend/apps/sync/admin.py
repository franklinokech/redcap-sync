from django.contrib import admin
from .models import SyncJob, SyncLog

class SyncLogInline(admin.TabularInline):
    model  = SyncLog
    extra  = 0
    readonly_fields = ["level", "message", "detail", "timestamp"]

@admin.register(SyncJob)
class SyncJobAdmin(admin.ModelAdmin):
    list_display  = ["id", "site_project", "sync_type", "status", "records_pulled", "records_pushed", "duration_secs", "triggered_by", "created_at"]
    list_filter   = ["status", "sync_type", "site_project__site"]
    search_fields = ["site_project__name"]
    readonly_fields = ["celery_task_id", "started_at", "completed_at", "created_at"]
    inlines       = [SyncLogInline]

@admin.register(SyncLog)
class SyncLogAdmin(admin.ModelAdmin):
    list_display  = ["job", "level", "message", "timestamp"]
    list_filter   = ["level"]
    search_fields = ["message"]