from django.contrib import admin
from .models import Site, SiteProject, APIToken

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display  = ["name", "code", "location", "status"]
    list_filter   = ["status"]
    search_fields = ["name", "code"]
    filter_horizontal = ["members"]

@admin.register(SiteProject)
class SiteProjectAdmin(admin.ModelAdmin):
    list_display  = ["name", "site", "status", "has_token", "project_id"]
    list_filter   = ["status", "site"]
    search_fields = ["name", "site__name"]

@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display  = ["project", "is_active", "token_preview", "created_at"]
    list_filter   = ["is_active"]
    readonly_fields = ["encrypted_token", "token_preview", "created_at"]