# apps/sync/views.py

from __future__ import annotations

import logging
from typing import Any

import requests
from django.conf import settings
from django.db import transaction
from django.db.models import Avg, Count, Max, Q, QuerySet, Sum
from django.utils import timezone
from rest_framework import status as http_status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.projects.models import SiteProject
from apps.registry.models import CentralRegistry

from .models import SyncJob, SyncLog
from .serializers import (
    PreviewSyncSerializer,
    SyncJobDetailSerializer,
    SyncJobListSerializer,
    SyncLogSerializer,
    SyncStatsSerializer,
    TriggerSyncSerializer,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _accessible_jobs(user) -> QuerySet[SyncJob]:
    """
    Return a SyncJob queryset scoped to what *user* may see.

    Staff / superusers see every job.
    Regular users see only jobs for projects belonging to their site(s).
    """
    qs = SyncJob.objects.select_related(
        "site_project__site",
        "registry",
        "triggered_by",
    )
    if user.is_staff or user.is_superuser:
        return qs
    return qs.filter(site_project__site__members=user)


def _resolve_registry(
    site_project: SiteProject,
    registry_id: int | None,
) -> CentralRegistry:
    """
    2-level registry resolution:

    1. Explicit *registry_id* from the request payload.
    2. Registry linked directly to the SiteProject.

    Raises ``ValueError`` if neither yields a result.
    """
    if registry_id:
        try:
            return CentralRegistry.objects.get(pk=registry_id)
        except CentralRegistry.DoesNotExist:
            raise ValueError(f"Registry {registry_id} not found.")

    if site_project.central_registry_id:
        return site_project.central_registry  # type: ignore[return-value]

    raise ValueError(
        "No registry specified and no registry is linked to this project. "
        "Link a registry via the project settings before triggering a sync."
    )


def _require_project_access(user, site_project: SiteProject) -> None:
    """Raise PermissionDenied unless *user* is staff or a member of the site."""
    if user.is_staff or user.is_superuser:
        return
    if not site_project.site.members.filter(pk=user.pk).exists():
        raise PermissionDenied


# ---------------------------------------------------------------------------
# Trigger
# ---------------------------------------------------------------------------


class TriggerSyncView(APIView):
    """POST /api/sync/trigger/<pk>/ — create and enqueue a SyncJob."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        # ── 1. Fetch & authorise ───────────────────────────────────────────
        try:
            site_project = SiteProject.objects.select_related(
                "site", "central_registry"
            ).get(pk=pk)
        except SiteProject.DoesNotExist:
            return Response(
                {"detail": "Project not found."},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        _require_project_access(request.user, site_project)

        # ── 2. Validate payload ────────────────────────────────────────────
        serializer = TriggerSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data: dict[str, Any] = serializer.validated_data

        # ── 3. Resolve registry ────────────────────────────────────────────
        try:
            registry = _resolve_registry(site_project, data.get("registry"))
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        # ── 4. 409 guard: reject if an active job already exists ───────────
        active_statuses = (SyncJob.Status.PENDING, SyncJob.Status.RUNNING)
        if SyncJob.objects.filter(
            site_project=site_project, status__in=active_statuses
        ).exists():
            return Response(
                {"detail": "A sync job is already active for this project."},
                status=http_status.HTTP_409_CONFLICT,
            )

        # ── 5. Create job record ───────────────────────────────────────────
        with transaction.atomic():
            job = SyncJob.objects.create(
                site_project=site_project,
                registry=registry,
                sync_type=data["sync_type"],
                date_from=data.get("date_from"),
                date_to=data.get("date_to"),
                triggered_by=request.user,
                # Snapshot the project's current form/field config so the job
                # record stays accurate even if config changes mid-run.
                forms_snapshot=site_project.sync_forms or "",
                fields_snapshot=site_project.sync_fields or "",
            )

        # ── 6. Enqueue Celery task ─────────────────────────────────────────
        # Deferred import avoids a circular import at module load time.
        from apps.sync.tasks import run_sync_job  # noqa: PLC0415

        run_sync_job.delay(job.pk)

        logger.info(
            "Sync job #%s created for project #%s by user %s",
            job.pk,
            pk,
            request.user,
        )
        return Response(
            SyncJobDetailSerializer(job).data,
            status=http_status.HTTP_202_ACCEPTED,
        )


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------


class PreviewSyncView(APIView):
    """POST /api/sync/preview/<pk>/ — dry-run preview via the R service."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        # Deferred to avoid import-time dependency on optional R client.
        from core.r_client import RServiceClient, RServiceError  # noqa: PLC0415

        # ── 1. Fetch & authorise ───────────────────────────────────────────
        try:
            site_project = SiteProject.objects.select_related("site").get(pk=pk)
        except SiteProject.DoesNotExist:
            return Response(
                {"detail": "Project not found."},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        _require_project_access(request.user, site_project)

        # ── 2. Validate payload ────────────────────────────────────────────
        # PreviewSyncSerializer accepts optional date_from / date_to only;
        # it does NOT accept sync_type (previews are always treated as FULL).
        serializer = PreviewSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data: dict[str, Any] = serializer.validated_data

        # ── 3. Resolve API token ───────────────────────────────────────────
        token_plaintext = site_project.get_active_token_plaintext()
        if token_plaintext is None:
            return Response(
                {"detail": "No active API token for this project."},
                status=http_status.HTTP_400_BAD_REQUEST,
            )

        # ── 4. Call R service ──────────────────────────────────────────────
        try:
            with RServiceClient() as client:
                result = client.preview(
                    token=token_plaintext,
                    redcap_url=site_project.redcap_url,
                    date_from=(
                        str(data["date_from"]) if data.get("date_from") else None
                    ),
                    date_to=(
                        str(data["date_to"]) if data.get("date_to") else None
                    ),
                )
        except RServiceError as exc:
            logger.warning(
                "Preview R-service error for project #%s: %s", pk, exc
            )
            return Response(
                {"detail": str(exc)},
                status=http_status.HTTP_502_BAD_GATEWAY,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Unexpected error in PreviewSyncView for project #%s", pk
            )
            return Response(
                {"detail": "Internal server error during preview."},
                status=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response(result, status=http_status.HTTP_200_OK)


# ---------------------------------------------------------------------------
# Job list
# ---------------------------------------------------------------------------


class SyncJobListView(ListAPIView):
    """GET /api/sync/jobs/ — paginated list of sync jobs."""

    permission_classes = [IsAuthenticated]
    serializer_class   = SyncJobListSerializer

    def get_queryset(self) -> QuerySet[SyncJob]:
        qs = (
            _accessible_jobs(self.request.user)
            .annotate(log_count_annotated=Count("logs"))
            .order_by("-created_at")
        )

        params = self.request.query_params

        # Filter helpers — walrus variables use unambiguous names to avoid
        # shadowing the `http_status` import used elsewhere in this module.
        if registry_id := params.get("registry"):
            qs = qs.filter(registry_id=registry_id)

        if job_sync_type := params.get("sync_type"):
            qs = qs.filter(sync_type=job_sync_type)

        if job_status := params.get("status"):
            qs = qs.filter(status=job_status.lower())

        if project_id := params.get("project"):
            qs = qs.filter(site_project_id=project_id)

        return qs


# ---------------------------------------------------------------------------
# Job detail
# ---------------------------------------------------------------------------


class SyncJobDetailView(APIView):
    """GET /api/sync/jobs/<pk>/ — full job detail including nested logs."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        try:
            job = (
                _accessible_jobs(request.user)
                .annotate(log_count_annotated=Count("logs"))
                .prefetch_related("logs")
                .get(pk=pk)
            )
        except SyncJob.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        return Response(SyncJobDetailSerializer(job).data)


# ---------------------------------------------------------------------------
# Job logs
# ---------------------------------------------------------------------------


class SyncJobLogsView(APIView):
    """GET /api/sync/jobs/<pk>/logs/ — paginated log entries for one job."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request, pk: int) -> Response:
        try:
            job = _accessible_jobs(request.user).get(pk=pk)
        except SyncJob.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        logs_qs = job.logs.order_by("timestamp")

        # Optional level filter — accept lowercase input gracefully
        if log_level := request.query_params.get("level"):
            logs_qs = logs_qs.filter(level=log_level.upper())

        return Response(SyncLogSerializer(logs_qs, many=True).data)


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


class CancelSyncView(APIView):
    """POST /api/sync/jobs/<pk>/cancel/ — cancel a PENDING or RUNNING job."""

    permission_classes = [IsAuthenticated]

    def post(self, request: Request, pk: int) -> Response:
        try:
            job = _accessible_jobs(request.user).get(pk=pk)
        except SyncJob.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        if not job.is_cancellable:
            return Response(
                {
                    "detail": "Job cannot be cancelled in its current state.",
                    "current_status": job.status,
                },
                status=http_status.HTTP_409_CONFLICT,
            )

        job.mark_cancelled()
        return Response(
            SyncJobDetailSerializer(job).data,
            status=http_status.HTTP_200_OK,
        )


# ---------------------------------------------------------------------------
# Retry
# ---------------------------------------------------------------------------


class RetryFailedSyncView(APIView):
    """
    POST /api/sync/jobs/<pk>/retry/

    Re-queues a FAILED or CANCELLED job by cloning its parameters into a
    new SyncJob and dispatching the Celery task.

    Returns 409 when:
    - The job's status is not FAILED or CANCELLED.
    - A PENDING / RUNNING job already exists for the same project.
    """

    permission_classes = [IsAuthenticated]
    RETRYABLE_STATUSES = frozenset({SyncJob.Status.FAILED, SyncJob.Status.CANCELLED})

    def post(self, request: Request, pk: int) -> Response:
        # ── 1. Fetch & authorise ───────────────────────────────────────────
        try:
            original = _accessible_jobs(request.user).get(pk=pk)
        except SyncJob.DoesNotExist:
            return Response(
                {"detail": "Not found."},
                status=http_status.HTTP_404_NOT_FOUND,
            )

        # ── 2. Guard: only retryable statuses ─────────────────────────────
        if original.status not in self.RETRYABLE_STATUSES:
            return Response(
                {
                    "detail": (
                        "Only FAILED or CANCELLED jobs can be retried. "
                        f"Current status: {original.get_status_display()}."
                    ),
                    "current_status": original.status,
                },
                status=http_status.HTTP_409_CONFLICT,
            )

        # ── 3. Guard: no concurrent active job ────────────────────────────
        active_statuses = (SyncJob.Status.PENDING, SyncJob.Status.RUNNING)
        if SyncJob.objects.filter(
            site_project=original.site_project,
            status__in=active_statuses,
        ).exists():
            return Response(
                {"detail": "A sync job is already active for this project."},
                status=http_status.HTTP_409_CONFLICT,
            )

        # ── 4. Clone into a new job ────────────────────────────────────────
        with transaction.atomic():
            new_job = SyncJob.objects.create(
                site_project=original.site_project,
                registry=original.registry,
                sync_type=original.sync_type,
                date_from=original.date_from,
                date_to=original.date_to,
                triggered_by=request.user,
                # Preserve original snapshots so the retry uses the exact
                # same form/field scope even if config changed since the
                # original job was created.
                forms_snapshot=original.forms_snapshot,
                fields_snapshot=original.fields_snapshot,
            )
            SyncLog.write(
                job=new_job,
                level=SyncLog.Level.INFO,
                message=(
                    f"Retry of job #{original.pk} triggered by "
                    f"{request.user.username}."
                ),
            )

        from apps.sync.tasks import run_sync_job  # noqa: PLC0415

        run_sync_job.delay(new_job.pk)
        logger.info(
            "Retry: new job #%s cloned from job #%s by user %s",
            new_job.pk,
            original.pk,
            request.user,
        )
        return Response(
            SyncJobDetailSerializer(new_job).data,
            status=http_status.HTTP_202_ACCEPTED,
        )


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class SyncStatsView(APIView):
    """GET /api/sync/stats/ — aggregate metrics across accessible jobs."""

    permission_classes = [IsAuthenticated]

    def get(self, request: Request) -> Response:
        qs = _accessible_jobs(request.user)

        agg: dict[str, Any] = qs.aggregate(
            total_jobs=Count("id"),
            pending_jobs=Count("id", filter=Q(status=SyncJob.Status.PENDING)),
            running_jobs=Count("id", filter=Q(status=SyncJob.Status.RUNNING)),
            successful_jobs=Count("id", filter=Q(status=SyncJob.Status.SUCCESS)),
            failed_jobs=Count("id", filter=Q(status=SyncJob.Status.FAILED)),
            cancelled_jobs=Count("id", filter=Q(status=SyncJob.Status.CANCELLED)),
            total_records_pulled=Sum("records_pulled"),
            total_records_pushed=Sum("records_pushed"),
            total_records_skipped=Sum("records_skipped"),
            avg_duration_secs=Avg("duration_secs"),
            last_sync_at=Max("created_at"),
            last_success_at=Max(
                "completed_at", filter=Q(status=SyncJob.Status.SUCCESS)
            ),
        )

        # Replace None (no rows / all-NULL column) with 0 for integer fields.
        for key in (
            "total_jobs",
            "pending_jobs",
            "running_jobs",
            "successful_jobs",
            "failed_jobs",
            "cancelled_jobs",
            "total_records_pulled",
            "total_records_pushed",
            "total_records_skipped",
        ):
            if agg[key] is None:
                agg[key] = 0

        serializer = SyncStatsSerializer(agg)
        return Response(serializer.data, status=http_status.HTTP_200_OK)



@api_view(['GET'])
@permission_classes([IsAuthenticated])
def r_health(request):
    """
    Proxy a health check to the R Plumber service.
    Returns 200 if R responds, 503 if it is unreachable or times out.
    """
    r_url = getattr(settings, 'R_SYNC_SERVICE_URL', 'http://localhost:8000')
    try:
        resp = requests.get(
            f"{r_url.rstrip('/')}/health",
            timeout=5,
        )
        resp.raise_for_status()
        return Response(
            {'status': 'up', 'r_status_code': resp.status_code},
            status=200,
        )
    except requests.exceptions.ConnectionError:
        return Response(
            {'status': 'down', 'detail': 'R service unreachable'},
            status=503,
        )
    except requests.exceptions.Timeout:
        return Response(
            {'status': 'down', 'detail': 'R service timed out'},
            status=503,
        )
    except requests.exceptions.HTTPError as exc:
        return Response(
            {'status': 'degraded', 'detail': str(exc)},
            status=503,
        )

