# apps/projects/views.py
from rest_framework import generics, status, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import Site, SiteProject, APIToken
from .serializers import (
    SiteSerializer, SiteCreateSerializer,
    SiteProjectSerializer, SiteProjectCreateSerializer,
    APITokenSerializer, APITokenCreateSerializer,
)


# ── Sites ─────────────────────────────────────────────────────────────────────

class SiteListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/projects/sites/       — list sites accessible to the user
    POST /api/projects/sites/       — create a new site (admin only)
    """

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return Site.objects.all()
        return Site.objects.filter(members=user)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SiteCreateSerializer
        return SiteSerializer

    def perform_create(self, serializer):
        if not (self.request.user.is_admin or self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only admins can create sites.")
        serializer.save()


class SiteDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/projects/sites/<id>/  — retrieve a site
    PATCH  /api/projects/sites/<id>/  — update a site
    DELETE /api/projects/sites/<id>/  — delete a site (admin only)
    """
    serializer_class = SiteSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_admin or user.is_superuser:
            return Site.objects.all()
        return Site.objects.filter(members=user)


class SiteMembersView(APIView):
    """
    POST   /api/projects/sites/<id>/members/  — add a user to a site
    DELETE /api/projects/sites/<id>/members/  — remove a user from a site
    """

    def post(self, request, pk):
        site    = get_object_or_404(Site, pk=pk)
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required."}, status=400)
        from apps.accounts.models import User
        user = get_object_or_404(User, pk=user_id)
        site.members.add(user)
        return Response({"detail": f"{user.username} added to {site.name}."})

    def delete(self, request, pk):
        site    = get_object_or_404(Site, pk=pk)
        user_id = request.data.get("user_id")
        if not user_id:
            return Response({"detail": "user_id is required."}, status=400)
        from apps.accounts.models import User
        user = get_object_or_404(User, pk=user_id)
        site.members.remove(user)
        return Response({"detail": f"{user.username} removed from {site.name}."})


# ── Site Projects ─────────────────────────────────────────────────────────────

class SiteProjectListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/projects/             — list all projects accessible to the user
    POST /api/projects/             — create a new project
    GET  /api/projects/?site=<id>   — filter by site
    """

    def get_queryset(self):
        user = self.request.user
        qs   = user.get_accessible_projects()

        # Optional filter by site
        site_id = self.request.query_params.get("site")
        if site_id:
            qs = qs.filter(site_id=site_id)

        # Optional filter by status
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        return qs.select_related("site")

    def get_serializer_class(self):
        if self.request.method == "POST":
            return SiteProjectCreateSerializer
        return SiteProjectSerializer


class SiteProjectDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/projects/<id>/   — retrieve a project
    PATCH  /api/projects/<id>/   — update a project
    DELETE /api/projects/<id>/   — delete a project
    """

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return SiteProjectCreateSerializer
        return SiteProjectSerializer

    def get_queryset(self):
        return self.request.user.get_accessible_projects()


# ── API Tokens ────────────────────────────────────────────────────────────────

class ProjectTokenView(APIView):
    """
    GET    /api/projects/<id>/token/   — get active token info (preview only)
    POST   /api/projects/<id>/token/   — add or rotate the project token
    DELETE /api/projects/<id>/token/   — deactivate the active token
    """

    def get_project(self, pk, user):
        return get_object_or_404(
            user.get_accessible_projects(), pk=pk
        )

    def get(self, request, pk):
        project = self.get_project(pk, request.user)
        token   = project.get_active_token()
        if not token:
            return Response({"detail": "No active token configured."}, status=404)
        return Response(APITokenSerializer(token).data)

    def post(self, request, pk):
        project    = self.get_project(pk, request.user)
        serializer = APITokenCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Deactivate existing tokens
        project.tokens.filter(is_active=True).update(is_active=False)

        # Create new encrypted token
        token = APIToken(
            project    = project,
            label      = serializer.validated_data.get("label", ""),
            created_by = request.user,
        )
        token.set_token(serializer.validated_data["token"])
        token.save()

        return Response(APITokenSerializer(token).data, status=status.HTTP_201_CREATED)

    def delete(self, request, pk):
        project = self.get_project(pk, request.user)
        updated = project.tokens.filter(is_active=True).update(is_active=False)
        if not updated:
            return Response({"detail": "No active token to deactivate."}, status=404)
        return Response({"detail": "Token deactivated."})


class ValidateTokenView(APIView):
    """
    POST /api/projects/<id>/validate-token/
    Calls the R plumber /project-info endpoint to verify the stored token
    works against the live REDCap instance.
    """

    def post(self, request, pk):
        from core.r_client import RServiceClient
        user    = request.user
        project = get_object_or_404(user.get_accessible_projects(), pk=pk)

        if not project.has_token():
            return Response(
                {"success": False, "message": "No active token configured for this project."},
                status=400,
            )

        try:
            token  = project.get_active_token_plaintext()
            client = RServiceClient()
            result = client.project_info(token=token, redcap_url=project.redcap_url)

            # Update project_id if returned
            if result.get("success") and result.get("info"):
                info = result["info"]
                if isinstance(info, list) and len(info) > 0:
                    info = info[0]
                project_id = info.get("project_id")
                if project_id:
                    project.project_id = project_id
                    project.save(update_fields=["project_id"])

            return Response(result)

        except Exception as e:
            return Response(
                {"success": False, "message": str(e)},
                status=500,
            )