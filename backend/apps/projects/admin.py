# apps/projects/admin.py
from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html, mark_safe
from django.urls import reverse

from .models import Site, SiteProject, APIToken


# ── Helpers ───────────────────────────────────────────────────────────────────

def _boolean_icon(value: bool) -> str:
    """Render a ✔/✘ icon for boolean columns."""
    if value:
        return mark_safe('<span style="color:#2e7d32;font-weight:bold;">&#10004;</span>')
    return mark_safe('<span style="color:#c62828;">&#10008;</span>')


# ── Site ──────────────────────────────────────────────────────────────────────

@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display      = ["name", "code", "location", "status"]
    list_filter       = ["status"]
    search_fields     = ["name", "code"]
    filter_horizontal = ["members"]
    date_hierarchy    = "created_at"

    fieldsets = [
        (None, {
            "fields": ["name", "code", "description", "location", "status"],
        }),
        ("Members", {
            "fields": ["members"],
        }),
        ("Audit", {
            "fields": ["created_by", "created_at"],
            "classes": ["collapse"],
        }),
    ]
    readonly_fields = ["created_at", "updated_at"]


# ── SiteProject ───────────────────────────────────────────────────────────────

@admin.register(SiteProject)
class SiteProjectAdmin(admin.ModelAdmin):

    list_display = [
        "name",
        "site",
        "status",
        "token_status",
        "project_id",
        "central_registry",
        "central_project_id",
    ]
    list_filter    = ["status", "site", "central_registry"]
    search_fields  = ["name", "site__name", "central_project_id"]
    date_hierarchy = "created_at"

    autocomplete_fields = ["site"]

    readonly_fields = ["created_at", "updated_at", "created_by"]

    fieldsets = [
        (None, {
            "fields": [
                "name",
                "site",
                "description",
                "status",
                "project_id",
                "redcap_url",
                "record_id_prefix",
            ],
        }),
        ("Sync settings", {
            # overwrite_with_blanks does not exist on the model — omitted
            "fields": ["sync_forms", "sync_fields"],
        }),
        ("Central Registry link", {
            "fields": ["central_registry", "central_project_id"],
            "description": (
                "Normally managed via the /api/projects/<id>/link-registry/ endpoint. "
                "Edit here only for emergency corrections."
            ),
        }),
        ("Audit", {
            "fields": ["created_by", "created_at", "updated_at"],
            "classes": ["collapse"],
        }),
    ]

    @admin.display(description="Token", ordering="api_tokens__is_active")
    def token_status(self, obj: SiteProject):
        return _boolean_icon(obj.has_token)


# ── APIToken ──────────────────────────────────────────────────────────────────

@admin.register(APIToken)
class APITokenAdmin(admin.ModelAdmin):
    list_display   = ("id", "project_link", "label", "active_icon", "preview_display", "created_at")
    list_filter    = ("is_active",)
    search_fields  = ("project__name", "label")
    date_hierarchy = "created_at"
    ordering       = ("-created_at",)

    readonly_fields = (
        "preview_display",
        "created_at",
        "updated_at",
        "created_by",
    )

    fieldsets = (
        (None, {
            "fields": ("project", "label", "is_active", "preview_display"),
        }),
        ("Audit", {
            "classes": ("collapse",),
            "fields": ("created_at", "updated_at", "created_by"),
        }),
    )

    # ── list display helpers ──────────────────────────────────────────────────

    @admin.display(description="Project", ordering="project__name")
    def project_link(self, obj: APIToken):
        if obj.project_id is None:
            return "—"
        url = reverse("admin:projects_siteproject_change", args=[obj.project_id])
        return format_html('<a href="{}">{}</a>', url, obj.project)

    @admin.display(description="Active")
    def active_icon(self, obj: APIToken):
        return _boolean_icon(obj.is_active)

    @admin.display(description="Token preview")
    def preview_display(self, obj: APIToken):
        value = obj.token_preview()          # call the method — note ()
        if not value or "?" in value:
            return mark_safe('<span style="color:#999;">—</span>')
        return format_html(
            '<code style="letter-spacing:0.05em;">{}</code>',
            value,
        )

    def has_add_permission(self, request):
        return False
