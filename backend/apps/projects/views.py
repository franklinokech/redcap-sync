# apps/projects/views.py
from rest_framework import generics, status, permissions
from rest_framework.exceptions import PermissionDenied, NotFound
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from .models import Site, SiteProject, APIToken
from .serializers import (
    SiteSerializer, SiteCreateSerializer,
    SiteProjectSerializer, SiteProjectCreateSerializer,
    APITokenSerializer, APITokenCreateSerializer,
)


# ── Permission helpers ────────────────────────────────────────────────────────

def _require_admin(user):
    """Raise PermissionDenied unless the user is an admin or superuser."""
    if not (user.is_admin or user.is_superuser):
        raise PermissionDenied("Only admins can perform this action.")


def _require_admin_or_manager(user):
    """Raise PermissionDenied unless admin, superuser, or site_manager."""
    if not (user.is_admin or user.is_superuser or user.role == "site_manager"):
        raise PermissionDenied("You do not have permission to perform this action.")


# ── Sites ─────────────────────────────────────────────────────────────────────

class SiteListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/projects/sites/  — list sites accessible to the requesting user
    POST /api/projects/sites/  — create a new site (admin only)
    """
    serializer_class = SiteSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return Site.objects.all()
        return Site.objects.filter(members=user)

    def perform_create(self, serializer):
        _require_admin(self.request.user)
        site = serializer.save(created_by=self.request.user)
        site.members.add(self.request.user)


class SiteDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/projects/sites/<id>/  — retrieve a site
    PATCH  /api/projects/sites/<id>/  — update a site (admin only)
    DELETE /api/projects/sites/<id>/  — delete a site (admin only)
    """
    serializer_class = SiteSerializer
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return Site.objects.all()
        return Site.objects.filter(members=user)

    def perform_update(self, serializer):
        _require_admin(self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        _require_admin(self.request.user)
        instance.delete()


class SiteMembersView(APIView):
    """
    GET    /api/projects/sites/<id>/members/  — list site members
    POST   /api/projects/sites/<id>/members/  — add a user to a site
    DELETE /api/projects/sites/<id>/members/  — remove a user from a site

    Body: { "user_id": <int> }
    """

    def get(self, request, pk):
        _require_admin_or_manager(request.user)
        site = get_object_or_404(Site, pk=pk)
        members = site.members.all().values(
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "role",
        )
        return Response(list(members), status=status.HTTP_200_OK)

    def _get_site_and_user(self, request, pk):
        _require_admin_or_manager(request.user)
        site    = get_object_or_404(Site, pk=pk)
        user_id = request.data.get("user_id")
        if not user_id:
            return None, None, Response(
                {"detail": "user_id is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        from apps.accounts.models import User
        target_user = get_object_or_404(User, pk=user_id)
        return site, target_user, None

    def post(self, request, pk):
        site, user, err = self._get_site_and_user(request, pk)
        if err:
            return err
        site.members.add(user)
        return Response({"detail": f"{user.username} added to {site.name}."})

    def delete(self, request, pk):
        site, user, err = self._get_site_and_user(request, pk)
        if err:
            return err
        site.members.remove(user)
        return Response({"detail": f"{user.username} removed from {site.name}."})


# ── Site Projects ─────────────────────────────────────────────────────────────

class SiteProjectListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/projects/  — list all projects accessible to the user
    POST /api/projects/  — create a new project (admin/manager only)

    Query params:
        site=<id>              filter by site
        status=<value>         filter by project status
        central_registry=<id>  filter by linked registry
        unlinked=true          only projects with no registry link
    """

    def get_queryset(self):
        user = self.request.user
        qs   = user.get_accessible_projects()

        site_id = self.request.query_params.get("site")
        if site_id:
            qs = qs.filter(site_id=site_id)

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        registry_id = self.request.query_params.get("central_registry")
        if registry_id:
            qs = qs.filter(central_registry_id=registry_id)

        if self.request.query_params.get("unlinked", "").lower() == "true":
            qs = qs.filter(central_registry__isnull=True)

        return qs.select_related("site", "central_registry")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SiteProjectCreateSerializer
        return SiteProjectSerializer

    def perform_create(self, serializer):
        _require_admin_or_manager(self.request.user)
        serializer.save()

    def create(self, request, *args, **kwargs):
        """
        Use CreateSerializer for input validation + write,
        then return the full SiteProjectSerializer response.
        """
        write_serializer = SiteProjectCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        write_serializer.is_valid(raise_exception=True)
        self.perform_create(write_serializer)
        instance = write_serializer.instance

        read_serializer = SiteProjectSerializer(
            instance,
            context={"request": request},
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class SiteProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/projects/<id>/  — retrieve a project
    PATCH  /api/projects/<id>/  — update a project (admin/manager only)
    DELETE /api/projects/<id>/  — delete a project (admin only)
    """
    http_method_names = ["get", "patch", "delete", "head", "options"]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return SiteProjectCreateSerializer
        return SiteProjectSerializer

    def get_queryset(self):
        return self.request.user.get_accessible_projects().select_related(
            "site", "central_registry"
        )

    def perform_update(self, serializer):
        _require_admin_or_manager(self.request.user)
        serializer.save()

    def perform_destroy(self, instance):
        _require_admin(self.request.user)
        instance.delete()

    def update(self, request, *args, **kwargs):
        """
        Use CreateSerializer for input validation + write,
        then return the full SiteProjectSerializer response.
        """
        instance = self.get_object()
        write_serializer = SiteProjectCreateSerializer(
            instance,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        write_serializer.is_valid(raise_exception=True)
        self.perform_update(write_serializer)

        read_serializer = SiteProjectSerializer(
            write_serializer.instance,
            context={"request": request},
        )
        return Response(read_serializer.data)


# ── Registry Link ─────────────────────────────────────────────────────────────

class LinkRegistryView(APIView):
    """
    POST   /api/projects/<id>/link-registry/  — set or update the registry link
    DELETE /api/projects/<id>/link-registry/  — remove the registry link

    POST body:
        {
            "central_registry":   <registry_id>,
            "central_project_id": <redcap_project_id>   (optional)
        }
    """

    def get_project(self, pk, user):
        return get_object_or_404(user.get_accessible_projects(), pk=pk)

    def post(self, request, pk):
        _require_admin_or_manager(request.user)
        project     = self.get_project(pk, request.user)
        registry_id = request.data.get("central_registry")
        project_id  = request.data.get("central_project_id")

        if not registry_id:
            return Response(
                {"detail": "central_registry is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        from apps.registry.models import CentralRegistry
        registry = get_object_or_404(CentralRegistry, pk=registry_id)

        project.central_registry   = registry
        project.central_project_id = project_id or None
        project.save(update_fields=["central_registry", "central_project_id"])

        return Response(SiteProjectSerializer(project).data)

    def delete(self, request, pk):
        _require_admin_or_manager(request.user)
        project = self.get_project(pk, request.user)

        if project.central_registry is None:
            return Response(
                {"detail": "This project is not linked to any registry."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        project.central_registry   = None
        project.central_project_id = None
        project.save(update_fields=["central_registry", "central_project_id"])

        return Response({"detail": "Registry link removed."})


# ── API Tokens ────────────────────────────────────────────────────────────────

class ProjectTokenView(APIView):
    """
    GET    /api/projects/<id>/token/  — get active token metadata
    POST   /api/projects/<id>/token/  — add or rotate the project token
    DELETE /api/projects/<id>/token/  — deactivate the active token
    """

    def get_project(self, pk, user):
        return get_object_or_404(user.get_accessible_projects(), pk=pk)

    def get(self, request, pk):
        project = self.get_project(pk, request.user)
        token   = project.get_active_token()
        if not token:
            return Response(
                {"detail": "No active token configured."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(APITokenSerializer(token).data)

    def post(self, request, pk):
        _require_admin_or_manager(request.user)
        project    = self.get_project(pk, request.user)
        serializer = APITokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = APIToken(
            project    = project,
            label      = serializer.validated_data.get("label", ""),
            created_by = request.user,
        )
        token.set_token(serializer.validated_data["token"])
        token.save()

        return Response(APITokenSerializer(token).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        _require_admin_or_manager(request.user)
        project = self.get_project(pk, request.user)
        updated = project.api_tokens.filter(is_active=True).update(is_active=False)
        if not updated:
            return Response(
                {"detail": "No active token to deactivate."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response({"detail": "Token deactivated."})


# ── Token Validation ──────────────────────────────────────────────────────────

class ValidateTokenView(APIView):
    """
    POST /api/projects/<id>/validate-token/

    Calls the R plumber /project-info endpoint to verify the stored token
    works against the live REDCap instance. Persists project_id on success.
    """

    def post(self, request, pk):
        from core.r_client import RServiceClient, RServiceError

        project = get_object_or_404(
            request.user.get_accessible_projects(), pk=pk
        )

        if not project.has_token:           # ← property, no ()
            return Response(
                {"success": False, "message": "No active token configured for this project."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            token  = project.get_active_token_plaintext()
            client = RServiceClient()
            result = client.validate_token(token=token, redcap_url=project.redcap_url)

            # Persist project_id returned by REDCap on success
            if result.get("success") and result.get("info"):
                info = result["info"]
                if isinstance(info, list) and len(info) > 0:
                    info = info[0]
                project_id = info.get("project_id")
                if project_id:
                    project.project_id = project_id
                    project.save(update_fields=["project_id"])

            return Response(result)

        except RServiceError as e:
            return Response(
                {"success": False, "message": str(e)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as e:
            return Response(
                {"success": False, "message": f"Unexpected error: {e}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
