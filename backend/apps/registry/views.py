# apps/registry/views.py

from __future__ import annotations

import logging

from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import MethodNotAllowed, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.r_client import (
    RServiceClient,
    RServiceError,
    RServiceValidationError,
)

from .models import CentralRegistry
from .serializers import CentralRegistryCreateSerializer, CentralRegistrySerializer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Permission helper
# ---------------------------------------------------------------------------


class IsAdminUser(permissions.BasePermission):
    """Allow access only to admin or superuser accounts."""

    message = "Only admins can manage the central registry."

    def has_permission(self, request, view) -> bool:
        return bool(
            request.user
            and request.user.is_authenticated
            and (
                getattr(request.user, "is_admin", False)
                or request.user.is_superuser
            )
        )


# ---------------------------------------------------------------------------
# Registry CRUD
# ---------------------------------------------------------------------------


class CentralRegistryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/registry/  -- list all registries (authenticated users)
    POST /api/registry/  -- create a new registry (admin only)
    """

    queryset = CentralRegistry.objects.all().order_by("-created_at")

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CentralRegistryCreateSerializer
        return CentralRegistrySerializer

    def create(self, request, *args, **kwargs):
        """Return full CentralRegistrySerializer representation after creation."""
        write_serializer = self.get_serializer(data=request.data)
        write_serializer.is_valid(raise_exception=True)
        instance = write_serializer.save()
        read_serializer = CentralRegistrySerializer(
            instance, context=self.get_serializer_context()
        )
        return Response(read_serializer.data, status=status.HTTP_201_CREATED)


class CentralRegistryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/registry/<id>/  -- retrieve (authenticated users)
    PATCH  /api/registry/<id>/  -- partial update (admin only)
    DELETE /api/registry/<id>/  -- delete (admin only)

    PUT is intentionally disabled -- use PATCH for partial updates.
    """

    queryset = CentralRegistry.objects.all()

    def get_permissions(self):
        if self.request.method in ("PATCH", "DELETE"):
            return [permissions.IsAuthenticated(), IsAdminUser()]
        return [permissions.IsAuthenticated()]

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return CentralRegistryCreateSerializer
        return CentralRegistrySerializer

    # ------------------------------------------------------------------
    # Disable PUT -- partial PATCH only
    # ------------------------------------------------------------------

    def put(self, request, *args, **kwargs):
        raise MethodNotAllowed(
            "PUT",
            detail="Full replacement is not supported. Use PATCH for partial updates.",
        )

    # ------------------------------------------------------------------
    # PATCH -- always partial
    # ------------------------------------------------------------------

    def patch(self, request, *args, **kwargs):
        kwargs["partial"] = True
        return super().patch(request, *args, **kwargs)

    # ------------------------------------------------------------------
    # DELETE -- guard against linked projects
    # ------------------------------------------------------------------

    def perform_destroy(self, instance: CentralRegistry) -> None:
        """Block deletion when projects are still linked to this registry."""
        if instance.is_in_use:
            raise ValidationError(
                f"Cannot delete registry '{instance.name}': "
                f"{instance.linked_projects_count} project(s) are still linked. "
                "Re-assign or unlink those projects first."
            )
        instance.delete()


# ---------------------------------------------------------------------------
# Token validation
# ---------------------------------------------------------------------------


class ValidateRegistryTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk: int):
        registry = get_object_or_404(CentralRegistry, pk=pk)

        # 1. Retrieve stored token
        try:
            token = registry.get_token()
        except ValueError as exc:
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 2. Call R service
        try:
            with RServiceClient() as client:
                result = client.validate_token(registry.redcap_url, token)

        except RServiceValidationError as exc:
            logger.warning(
                "ValidateRegistryTokenView: validation error for registry %s: %s",
                pk, exc,
            )
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except RServiceError as exc:
            logger.error(
                "ValidateRegistryTokenView: R service error for registry %s: %s",
                pk, exc,
            )
            return Response(
                {"success": False, "message": str(exc)},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except Exception:
            logger.exception(
                "ValidateRegistryTokenView: unexpected error for registry %s", pk
            )
            return Response(
                {"success": False, "message": "Unexpected error during validation."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        # 3. Persist project_id  ← field is project_id, NOT redcap_id
        raw_project_id = result.get("project_id")
        if raw_project_id is not None:
            new_id = int(raw_project_id)
            if new_id != registry.project_id:
                registry.project_id = new_id
                registry.save(update_fields=["project_id"])
                logger.info(
                    "ValidateRegistryTokenView: set project_id=%s for registry %s",
                    new_id, pk,
                )

        # 4. Return stable JSON contract
        return Response(
            {
                "success":        True,
                "project_id":     registry.project_id,
                "redcap_version": result.get("redcap_version", "unknown"),
                "project_title":  result.get("project_title", "Unknown"),
            },
            status=status.HTTP_200_OK,
        )

