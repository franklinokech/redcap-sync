# apps/projects/models.py
from __future__ import annotations

from django.db import models
from django.conf import settings
from cryptography.fernet import Fernet, InvalidToken
import logging

logger = logging.getLogger(__name__)


# ── Encryption helpers ────────────────────────────────────────────────────────

def _fernet():
    """
    Return a Fernet cipher using REDCAP_TOKEN_ENCRYPTION_KEY from settings.
    Generate a key with:
        python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    """
    key = getattr(settings, "REDCAP_TOKEN_ENCRYPTION_KEY", "")
    if not key:
        raise ValueError(
            "REDCAP_TOKEN_ENCRYPTION_KEY is not configured. "
            "Set it in your .env file."
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_token(raw_token: str) -> str:
    """Encrypt a plaintext REDCap token and return the ciphertext string."""
    cleaned = raw_token.strip()
    if len(cleaned) != 32:
        raise ValueError("REDCap API tokens must be exactly 32 characters.")
    if not cleaned.isalnum():
        raise ValueError("REDCap API tokens must be alphanumeric (hex string).")
    return _fernet().encrypt(cleaned.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored token ciphertext and return plaintext."""
    try:
        return _fernet().decrypt(encrypted_token.encode()).decode()
    except InvalidToken:
        raise ValueError(
            "Token decryption failed — the encryption key may have changed."
        )


# ── Site ──────────────────────────────────────────────────────────────────────

class Site(models.Model):
    """
    A physical or organisational site that hosts one or more REDCap projects.
    """

    class Status(models.TextChoices):
        ACTIVE   = "active",   "Active"
        INACTIVE = "inactive", "Inactive"

    name        = models.CharField(max_length=255, unique=True)
    code        = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short identifier used in logs and displays, e.g. NBI-01",
    )
    description = models.TextField(blank=True)
    location    = models.CharField(max_length=255, blank=True)
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        blank=True,
        related_name="sites",
        help_text="Users who can view and manage this site's projects",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_sites",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = "projects_site"
        ordering            = ["name"]
        verbose_name        = "Site"
        verbose_name_plural = "Sites"

    def __str__(self):
        return f"{self.name} ({self.code})"

    def active_projects(self):
        return self.projects.filter(status=SiteProject.Status.ACTIVE)


# ── SiteProject ───────────────────────────────────────────────────────────────

class SiteProject(models.Model):
    """
    A single REDCap project hosted at a site.

    The sync engine pulls records from this project's REDCap instance
    (authenticated via APIToken) and pushes them to the linked CentralRegistry.
    """

    class Status(models.TextChoices):
        ACTIVE   = "active",   "Active"
        INACTIVE = "inactive", "Inactive"
        TESTING  = "testing",  "Testing"

    site        = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="projects",
    )
    name        = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    redcap_url  = models.URLField(
        max_length=500,
        help_text="Full REDCap API URL, e.g. https://redcap.site.ac.ke/api/",
    )
    project_id  = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="REDCap internal project ID — fetched automatically on token validation",
    )
    status      = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
    )

    sync_forms  = models.TextField(
        blank=True,
        help_text="JSON array of REDCap form names to sync. Leave blank for all.",
    )
    sync_fields = models.TextField(
        blank=True,
        help_text="JSON array of field names to sync. Leave blank for all.",
    )
    record_id_prefix = models.CharField(
        max_length=20,
        blank=True,
        help_text="Prefix added to record IDs before pushing, e.g. 'NBI-'",
    )

    # ── Central Registry link ─────────────────────────────────────────────────
    central_registry = models.ForeignKey(
        "registry.CentralRegistry",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_site_projects",
        help_text="The central registry this project syncs into",
    )
    central_project_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="REDCap project ID on the central registry — verified before syncing",
    )
    # ─────────────────────────────────────────────────────────────────────────

    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_projects",
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = "projects_site_project"
        ordering            = ["site__name", "name"]
        verbose_name        = "Site Project"
        verbose_name_plural = "Site Projects"
        unique_together     = [("site", "name")]

    def __str__(self):
        return f"{self.site.code} / {self.name}"

    # ── Token helpers ─────────────────────────────────────────────────────────

    @property
    def has_token(self) -> bool:
        """Return True if an active API token exists for this project."""
        return self.api_tokens.filter(is_active=True).exists()

    def get_active_token(self):
        """Return the active APIToken instance, or None."""
        return self.api_tokens.filter(is_active=True).first()

    def get_active_token_plaintext(self) -> str | None:
        """Decrypt and return the active token value, or None if not set."""
        token_obj = self.get_active_token()
        if not token_obj:
            return None
        return token_obj.get_plaintext()

    # ── Sync filter helpers ───────────────────────────────────────────────────

    def get_sync_forms_list(self) -> list[str] | None:
        """Return sync_forms as a list, or None (meaning all forms)."""
        if self.sync_forms.strip():
            return [f.strip() for f in self.sync_forms.split(",") if f.strip()]
        return None

    def get_sync_fields_list(self) -> list[str] | None:
        """Return sync_fields as a list, or None (meaning all fields)."""
        if self.sync_fields.strip():
            return [f.strip() for f in self.sync_fields.split(",") if f.strip()]
        return None


# ── APIToken ──────────────────────────────────────────────────────────────────

class APIToken(models.Model):
    """
    Stores an encrypted REDCap API token for a SiteProject.

    Only one token per project can be active at a time.
    Old tokens are deactivated (not deleted) to preserve audit history.
    """

    project    = models.ForeignKey(
        SiteProject,
        on_delete=models.CASCADE,
        related_name="api_tokens",
    )
    token      = models.TextField(blank=True,default="", help_text="Fernet-encrypted REDCap API token")
    label      = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional note, e.g. 'Rotated Jan 2025'",
    )
    is_active  = models.BooleanField(default=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "projects_api_token"
        ordering = ["-created_at"]

    def __str__(self):
        status = "active" if self.is_active else "inactive"
        return f"Token for {self.project} ({status})"

    # ── Encryption helpers ────────────────────────────────────────────────────

    def set_token(self, plaintext: str) -> None:
        """Encrypt and store a plaintext token."""
        self.token = encrypt_token(plaintext)

    def get_plaintext(self) -> str:
        """Decrypt and return the plaintext token. Raises ValueError on bad key."""
        return decrypt_token(self.token)

    def token_preview(self) -> str:
        """Return first-4 + mask + last-4, e.g. 'A1B2****F7G8'."""
        try:
            plain = self.get_plaintext()
            if len(plain) >= 8:
                return f"{plain[:4]}****{plain[-4:]}"
            return "????????"
        except Exception:
            return "????????"

    # ── Save hook — enforce one active token per project ──────────────────────

    def save(self, *args, **kwargs):
        if self.is_active:
            qs = APIToken.objects.filter(project=self.project, is_active=True)
            if self.pk:
                qs = qs.exclude(pk=self.pk)
            qs.update(is_active=False)
        super().save(*args, **kwargs)
