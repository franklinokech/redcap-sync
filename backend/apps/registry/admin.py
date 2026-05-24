# apps/registry/admin.py
from __future__ import annotations

from django.contrib import admin
from django.utils.html import format_html, mark_safe

from .models import CentralRegistry


@admin.register(CentralRegistry)
class CentralRegistryAdmin(admin.ModelAdmin):

    # ------------------------------------------------------------------
    # List view
    # ------------------------------------------------------------------

    list_display = [
        "name",
        "redcap_url",
        "project_id",
        "has_token_icon",
        "linked_projects_display",
        "is_in_use_icon",
        "overwrite_with_blanks",
        "created_by",
        "created_at",
    ]
    list_filter = [
        "overwrite_with_blanks",
        "created_at",
    ]
    search_fields = [
        "name",
        "description",
        "redcap_url",
    ]
    date_hierarchy = "created_at"
    ordering = ["-created_at"]

    # ------------------------------------------------------------------
    # Detail view
    # ------------------------------------------------------------------

    readonly_fields = [
        "project_id",
        "token_preview_display",
        "linked_projects_display",
        "is_in_use_icon",
        "has_token_icon",
        "created_by",
        "created_at",
        "updated_at",
    ]
    fieldsets = (
        (
            "Identity",
            {
                "fields": ("name", "description"),
            },
        ),
        (
            "REDCap Connection",
            {
                "fields": (
                    "redcap_url",
                    "project_id",
                    "has_token_icon",
                    "token_preview_display",
                ),
            },
        ),
        (
            "Sync Behaviour",
            {
                "fields": ("overwrite_with_blanks",),
            },
        ),
        (
            "Usage",
            {
                "fields": (
                    "linked_projects_display",
                    "is_in_use_icon",
                ),
            },
        ),
        (
            "Audit",
            {
                "classes": ("collapse",),
                "fields": ("created_by", "created_at", "updated_at"),
            },
        ),
    )

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def save_model(self, request, obj, form, change):
        """Stamp created_by on first save."""
        if not change and obj.created_by_id is None:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    # ------------------------------------------------------------------
    # Custom display helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _boolean_icon(value: bool):
        """
        Return a coloured ✔/✘ HTML span.

        Must use mark_safe for fully static strings — format_html with no {}
        placeholder raises TypeError in Django 4.2+.
        """
        if value:
            return mark_safe(
                '<span style="color:#2e7d32;font-size:1.1em" title="Yes">&#10004;</span>'
            )
        return mark_safe(
            '<span style="color:#c62828;font-size:1.1em" title="No">&#10008;</span>'
        )

    @admin.display(description="Token?", ordering="encrypted_token")
    def has_token_icon(self, obj: CentralRegistry):
        return self._boolean_icon(obj.has_token)

    @admin.display(description="Token Preview")
    def token_preview_display(self, obj: CentralRegistry):
        preview = obj.token_preview  # e.g. "821E****BE42" or ""
        if not preview:
            return mark_safe('<span style="color:#999;">—</span>')
        # preview contains user-derived data — escape it via format_html
        return format_html(
            '<code style="letter-spacing:0.05em">{}</code>',
            preview,
        )

    @admin.display(description="Linked Projects")
    def linked_projects_display(self, obj: CentralRegistry) -> int:
        return obj.linked_projects_count

    @admin.display(description="In Use?")
    def is_in_use_icon(self, obj: CentralRegistry):
        return self._boolean_icon(obj.is_in_use)
