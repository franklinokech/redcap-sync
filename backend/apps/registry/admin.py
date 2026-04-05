from django.contrib import admin
from .models import CentralRegistry

@admin.register(CentralRegistry)
class CentralRegistryAdmin(admin.ModelAdmin):
    list_display    = ["name", "redcap_url", "is_active", "project_id"]
    readonly_fields = ["encrypted_token", "token_preview", "created_at"]