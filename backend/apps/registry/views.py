# apps/registry/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import CentralRegistry
from .serializers import CentralRegistrySerializer, CentralRegistryCreateSerializer


class CentralRegistryListCreateView(generics.ListCreateAPIView):
    """
    GET  /api/registry/   — list all registries
    POST /api/registry/   — create a new registry (admin only)
    """
    queryset = CentralRegistry.objects.all()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return CentralRegistryCreateSerializer
        return CentralRegistrySerializer

    def perform_create(self, serializer):
        if not (self.request.user.is_admin or self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only admins can configure the registry.")
        serializer.save()


class CentralRegistryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/registry/<id>/   — retrieve registry
    PATCH  /api/registry/<id>/   — update registry
    DELETE /api/registry/<id>/   — delete registry
    """
    queryset = CentralRegistry.objects.all()

    def get_serializer_class(self):
        if self.request.method in ("PATCH", "PUT"):
            return CentralRegistryCreateSerializer
        return CentralRegistrySerializer


class ActiveRegistryView(APIView):
    """
    GET /api/registry/active/  — return the currently active registry
    """

    def get(self, request):
        registry = CentralRegistry.get_active()
        if not registry:
            return Response(
                {"detail": "No active registry configured."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(CentralRegistrySerializer(registry).data)


class ValidateRegistryTokenView(APIView):
    """
    POST /api/registry/<id>/validate-token/
    Verify the registry token works against the live REDCap instance.
    """

    def post(self, request, pk):
        from core.r_client import RServiceClient
        registry = get_object_or_404(CentralRegistry, pk=pk)

        try:
            token  = registry.get_token()
            client = RServiceClient()
            result = client.project_info(token=token, redcap_url=registry.redcap_url)

            if result.get("success") and result.get("info"):
                info = result["info"]
                if isinstance(info, list) and len(info) > 0:
                    info = info[0]
                project_id = info.get("project_id")
                if project_id:
                    registry.project_id = project_id
                    registry.save(update_fields=["project_id"])

            return Response(result)

        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=500)