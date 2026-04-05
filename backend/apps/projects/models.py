# apps/projects/models.py
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
    if len(raw_token.strip()) != 32:
        raise ValueError("REDCap API tokens must be exactly 32 characters.")
    return _fernet().encrypt(raw_token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """Decrypt a stored token ciphertext and return plaintext."""
    try:
        return _fernet().decrypt(encrypted_token.encode()).decode()
    except InvalidToken:
        raise ValueError(
            "Token decryption failed — the encryption key may have changed."
        )


# ── Site ─────────────────────────────────────────────────────────────────────

class Site(models.Model):
    """
    A physical or organisational site that hosts one or more REDCap projects.

    Examples:
      - "Nairobi County Hospital"
      - "Kisumu Research Centre"
      - "Mombasa Field Office"

    A site is the top-level grouping. Users are assigned to sites; projects
    belong to sites. One site can have many projects.
    """

    class Status(models.TextChoices):
        ACTIVE   = "active",   "Active"
        INACTIVE = "inactive", "Inactive"

    name        = models.CharField(max_length=255, unique=True, help_text="Full name of the site")
    code        = models.CharField(
        max_length=20,
        unique=True,
        help_text="Short identifier used in logs and displays, e.g. NBI-01",
    )
    description = models.TextField(blank=True)
    location    = models.CharField(max_length=255, blank=True, help_text="City, county, or region")
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Users assigned to this site (non-admin users see only their site's projects)
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

    One site can have many projects (enrollment, follow-up, lab results, etc.).
    Each project has its own API token stored separately in APIToken.

    The sync engine pulls from this project and pushes to the CentralRegistry.
    """

    class Status(models.TextChoices):
        ACTIVE   = "active",   "Active"
        INACTIVE = "inactive", "Inactive"
        TESTING  = "testing",  "Testing"

    site        = models.ForeignKey(
        Site,
        on_delete=models.CASCADE,
        related_name="projects",
        help_text="The site this project belongs to",
    )
    name        = models.CharField(
        max_length=255,
        help_text="Descriptive name, e.g. 'Nairobi — Enrollment Form'",
    )
    description = models.TextField(blank=True)
    redcap_url  = models.URLField(
        max_length=500,
        help_text="Full REDCap API URL for this project, e.g. https://redcap.site.ac.ke/api/",
    )
    # Populated automatically when the user validates the token via /project-info
    project_id  = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="REDCap internal project ID — fetched automatically on token validation",
    )
    status      = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    # Optional field/form scoping (blank = sync everything)
    sync_forms  = models.TextField(
        blank=True,
        help_text="Comma-separated REDCap form names to include in sync. Leave blank for all forms.",
    )
    sync_fields = models.TextField(
        blank=True,
        help_text="Comma-separated field names to include in sync. Leave blank for all fields.",
    )

    # Record ID remapping: some sites prefix record IDs to avoid collisions in the registry
    record_id_prefix = models.CharField(
        max_length=20,
        blank=True,
        help_text="Optional prefix added to record IDs before pushing to registry, e.g. 'NBI-'",
    )

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
        # Prevent duplicate project names within the same site
        unique_together     = [("site", "name")]

    def __str__(self):
        return f"{self.site.code} / {self.name}"

    def has_token(self):
        """Return True if an active API token exists for this project."""
        return self.tokens.filter(is_active=True).exists()

    def get_active_token(self):
        """Return the active APIToken instance, or None."""
        return self.tokens.filter(is_active=True).first()

    def get_active_token_plaintext(self):
        """Decrypt and return the active token value, or raise if none."""
        token_obj = self.get_active_token()
        if not token_obj:
            raise ValueError(f"No active API token configured for project '{self.name}'.")
        return token_obj.get_token()

    def get_sync_forms_list(self):
        """Return sync_forms as a list, or None (meaning all forms)."""
        if self.sync_forms.strip():
            return [f.strip() for f in self.sync_forms.split(",") if f.strip()]
        return None

    def get_sync_fields_list(self):
        """Return sync_fields as a list, or None (meaning all fields)."""
        if self.sync_fields.strip():
            return [f.strip() for f in self.sync_fields.split(",") if f.strip()]
        return None


# ── APIToken ──────────────────────────────────────────────────────────────────

class APIToken(models.Model):
    """
    Encrypted REDCap API token for a SiteProject.

    A project can have multiple token records (history), but only one
    is_active=True at a time. Tokens are encrypted at rest using Fernet
    symmetric encryption — the plaintext is never stored.

    Token rotation: deactivate the old token, create a new one.
    """

    project         = models.ForeignKey(
        SiteProject,
        on_delete=models.CASCADE,
        related_name="tokens",
        help_text="The project this token authenticates against",
    )
    label           = models.CharField(
        max_length=100,
        blank=True,
        help_text="Optional label, e.g. 'Production token — added Jan 2025'",
    )
    encrypted_token = models.TextField(help_text="Fernet-encrypted REDCap API token — never stored in plaintext")
    is_active       = models.BooleanField(
        default=True,
        help_text="Only one token per project should be active at a time",
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_tokens",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = "projects_api_token"
        ordering            = ["-created_at"]
        verbose_name        = "API Token"
        verbose_name_plural = "API Tokens"

    def __str__(self):
        status = "active" if self.is_active else "inactive"
        return f"Token [{status}] — {self.project}"

    def set_token(self, raw_token: str):
        """Encrypt and store a plaintext REDCap token."""
        self.encrypted_token = encrypt_token(raw_token)

    def get_token(self) -> str:
        """Decrypt and return the plaintext token."""
        return decrypt_token(self.encrypted_token)

    def token_preview(self) -> str:
        """First 4 chars + masked remainder — safe for display."""
        try:
            plain = self.get_token()
            return plain[:4] + "*" * (len(plain) - 4)
        except Exception:
            return "****"

    def save(self, *args, **kwargs):
        # When activating a token, deactivate all others for the same project
        if self.is_active and self.pk:
            APIToken.objects.filter(
                project=self.project,
                is_active=True,
            ).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)