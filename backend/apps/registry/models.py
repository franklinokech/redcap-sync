# apps/registry/models.py
from django.db import models
from django.conf import settings
from apps.projects.models import encrypt_token, decrypt_token
import logging

logger = logging.getLogger(__name__)


class CentralRegistry(models.Model):
    """
    The central REDCap project that all site data is synced into.

    There should be exactly one active registry at a time.
    When a new registry is set to is_active=True, all others are
    automatically deactivated via the save() override.

    The registry token is encrypted at rest using the same Fernet
    mechanism as SiteProject tokens.
    """

    name        = models.CharField(
        max_length=255,
        help_text="Descriptive name, e.g. 'National TB Registry — Production'",
    )
    description = models.TextField(blank=True)
    redcap_url  = models.URLField(
        max_length=500,
        help_text="Central registry REDCap API URL",
    )
    project_id  = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="REDCap internal project ID — fetched on token validation",
    )

    encrypted_token = models.TextField(
        help_text="Fernet-encrypted registry API token",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Only one registry should be active at a time",
    )

    # Sync behaviour options
    overwrite_with_blanks = models.BooleanField(
        default=False,
        help_text=(
            "If True, blank values from source will overwrite existing data in registry. "
            "Keep False unless intentional."
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

    def __str__(self):
        flag = " [ACTIVE]" if self.is_active else ""
        return f"{self.name}{flag}"

    def set_token(self, raw_token: str):
        """Encrypt and store the registry API token."""
        self.encrypted_token = encrypt_token(raw_token)

    def get_token(self) -> str:
        """Decrypt and return the plaintext registry token."""
        return decrypt_token(self.encrypted_token)

    def token_preview(self) -> str:
        """First 4 chars + masked remainder — safe for display."""
        try:
            plain = self.get_token()
            return plain[:4] + "*" * (len(plain) - 4)
        except Exception:
            return "****"

    def save(self, *args, **kwargs):
        # Enforce single active registry
        if self.is_active:
            CentralRegistry.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

    @classmethod
    def get_active(cls):
        """Return the currently active registry, or None."""
        return cls.objects.filter(is_active=True).first()