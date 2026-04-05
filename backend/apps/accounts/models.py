# apps/accounts/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """
    Extended user model with role-based access.

    Roles:
      admin        — full access to all sites, projects, registry config, and users
      site_manager — can manage projects and trigger syncs for their assigned sites only
      viewer       — read-only access to logs and dashboards for their assigned sites

    A user's access to specific sites is controlled via the Site.members M2M,
    not stored directly on this model.
    """

    class Role(models.TextChoices):
        ADMIN        = "admin",        "Admin"
        SITE_MANAGER = "site_manager", "Site Manager"
        VIEWER       = "viewer",       "Viewer"

    role         = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )
    organisation = models.CharField(
        max_length=255,
        blank=True,
        help_text="Institution or facility name this user belongs to",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table            = "accounts_user"
        ordering            = ["username"]
        verbose_name        = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

    @property
    def is_admin(self):
        return self.role == self.Role.ADMIN

    @property
    def is_site_manager(self):
        return self.role == self.Role.SITE_MANAGER

    def get_accessible_projects(self):
        """
        Return all SiteProjects this user can access.
        Admins get everything; others get projects belonging to their assigned sites.
        """
        from apps.projects.models import SiteProject
        if self.is_admin or self.is_superuser:
            return SiteProject.objects.all()
        return SiteProject.objects.filter(site__members=self)