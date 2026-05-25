# apps/registry/models.py
from django.db import models
from django.conf import settings

from apps.projects.models import encrypt_token, decrypt_token
import logging

logger = logging.getLogger(__name__)


class CentralRegistry(models.Model):
    """
    A central REDCap project that site data can be synced into.

    Multiple registries can coexist. Each SiteProject is linked to
    exactly one registry via a ForeignKey. There is no longer a global
    'active' registry -- registry resolution is always per-project.

    The registry token is encrypted at rest using the same Fernet
    mechanism as SiteProject tokens.
    """

    name = models.CharField(
        max_length=255,
        help_text=(
            "Descriptive name identifying the organisation, clinical area, and environment. "
            "e.g. 'KWTRP Neonatal Registry - Production' or "
            "'KWTRP Neonatal Registry - Staging'"
        ),
    )
    description = models.TextField(blank=True)
    redcap_url = models.URLField(
        max_length=500,
        help_text="Central registry REDCap API URL",
    )
    project_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="REDCap internal project ID -- fetched on token validation",
    )
    encrypted_token = models.TextField(
        blank=True,          # allows explicit validation in serializer/form
        default="",
        help_text="Fernet-encrypted registry API token",
    )

    # Sync behaviour
    overwrite_with_blanks = models.BooleanField(
        default=False,
        help_text=(
            "If True, blank values from the source will overwrite existing data "
            "in the registry. Keep False unless intentional."
        ),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_registries",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = "registry_central_registry"
        ordering            = ["-created_at"]
        verbose_name        = "Central Registry"
        verbose_name_plural = "Central Registries"

    def __str__(self) -> str:
        pid = f" [PID: {self.project_id}]" if self.project_id else ""
        return f"{self.name}{pid}"

    # ------------------------------------------------------------------
    # Token helpers
    # ------------------------------------------------------------------

    def set_token(self, raw_token: str) -> None:
        """Encrypt and store the registry API token."""
        self.encrypted_token = encrypt_token(raw_token)

    @property
    def has_token(self) -> bool:
        """True if an encrypted token has been stored."""
        return bool(self.encrypted_token)

    def get_token(self) -> str:
        """
        Decrypt and return the plaintext registry token.

        Raises ValueError if no token has been stored yet.
        Raises cryptography.fernet.InvalidToken if the stored value
        is corrupt or was encrypted with a different key.
        """
        if not self.encrypted_token:
            raise ValueError(
                f"CentralRegistry '{self.name}' (pk={self.pk}) has no token stored."
            )
        return decrypt_token(self.encrypted_token)

    @property
    def token_preview(self) -> str:
        """First 4 chars + bullet-masked remainder -- safe for display."""
        if not self.encrypted_token:
            return "—"
        try:
            plain = self.get_token()
            return plain[:4] + "•" * max(len(plain) - 4, 0)
        except Exception:
            logger.warning(
                "token_preview: failed to decrypt token for registry pk=%s", self.pk
            )
            return "••••"

    # ------------------------------------------------------------------
    # Linked-projects helpers
    # ------------------------------------------------------------------

    @property
    def linked_projects_count(self) -> int:
        return self.linked_site_projects.count()

    @property
    def is_in_use(self) -> bool:
        """
        True if at least one SiteProject references this registry.
        Used to guard against accidental deletion of a registry that
        is actively serving sync jobs.
        """
        return self.linked_site_projects.exists()
