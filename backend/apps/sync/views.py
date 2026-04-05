# apps/sync/views.py
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from .models import SyncJob, SyncLog
from .serializers import SyncJobSerializer, SyncLogSerializer, TriggerSyncSerializer
from apps.projects.models import SiteProject
from apps.registry.models import CentralRegistry
import logging

logger = logging.getLogger(__name__)


class TriggerSyncView(APIView):
    def post(self, request):
        serializer = TriggerSyncSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        project = get_object_or_404(
            request.user.get_accessible_projects(),
            pk=data["site_project"],
        )

        registry_id = data.get("registry")
        if registry_id:
            registry = get_object_or_404(CentralRegistry, pk=registry_id)
        else:
            registry = CentralRegistry.get_active()
            if not registry:
                return Response(
                    {"detail": "No active registry configured."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        if not project.has_token():
            return Response(
                {"detail": f"No active token for project '{project.name}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        job = SyncJob.objects.create(
            site_project    = project,
            registry        = registry,
            sync_type       = data["sync_type"],
            date_from       = data.get("date_from"),
            date_to         = data.get("date_to"),
            forms_snapshot  = project.sync_forms  or "",
            fields_snapshot = project.sync_fields or "",
            triggered_by    = request.user,
        )

        SyncLog.write(job, "INFO", f"Sync job created by {request.user.username}")

        from apps.sync.tasks import run_sync_job
        task = run_sync_job.delay(job.pk)

        job.celery_task_id = task.id
        job.save(update_fields=["celery_task_id"])

        SyncLog.write(job, "INFO", f"Queued in Celery (task_id={task.id})")
        logger.info("Sync job %s queued — task_id=%s", job.pk, task.id)

        return Response(
            SyncJobSerializer(job).data,
            status=status.HTTP_202_ACCEPTED,
        )


class CancelSyncView(APIView):
    def post(self, request, pk):
        accessible = request.user.get_accessible_projects()
        job = get_object_or_404(
            SyncJob.objects.filter(site_project__in=accessible),
            pk=pk,
        )

        if job.is_complete:
            return Response(
                {"detail": f"Job is already {job.status} — cannot cancel."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if job.celery_task_id:
            from config.celery import app as celery_app
            celery_app.control.revoke(job.celery_task_id, terminate=True)

        job.status = SyncJob.Status.CANCELLED
        job.save(update_fields=["status"])
        SyncLog.write(job, "WARNING", f"Job cancelled by {request.user.username}")

        return Response({"detail": "Job cancelled.", "job_id": job.pk})


class PreviewSyncView(APIView):
    def post(self, request):
        project_id = request.data.get("site_project")
        if not project_id:
            return Response({"detail": "site_project is required."}, status=400)

        project = get_object_or_404(
            request.user.get_accessible_projects(), pk=project_id
        )

        if not project.has_token():
            return Response(
                {"detail": "No active token configured for this project."},
                status=400,
            )

        try:
            from core.r_client import RServiceClient
            client = RServiceClient()
            result = client.preview(
                token      = project.get_active_token_plaintext(),
                redcap_url = project.redcap_url,
                sync_type  = request.data.get("sync_type", "full"),
                date_from  = request.data.get("date_from"),
                date_to    = request.data.get("date_to"),
            )
            return Response(result)
        except Exception as e:
            return Response({"success": False, "message": str(e)}, status=500)


class SyncJobListView(generics.ListAPIView):
    serializer_class = SyncJobSerializer

    def get_queryset(self):
        user = self.request.user
        qs   = SyncJob.objects.filter(
            site_project__in=user.get_accessible_projects()
        ).select_related(
            "site_project", "site_project__site",
            "registry", "triggered_by"
        )

        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(site_project_id=project_id)

        site_id = self.request.query_params.get("site")
        if site_id:
            qs = qs.filter(site_project__site_id=site_id)

        job_status = self.request.query_params.get("status")
        if job_status:
            qs = qs.filter(status=job_status)

        return qs


class SyncJobDetailView(generics.RetrieveAPIView):
    serializer_class = SyncJobSerializer

    def get_queryset(self):
        accessible = self.request.user.get_accessible_projects()
        return SyncJob.objects.filter(site_project__in=accessible)


class SyncJobLogsView(generics.ListAPIView):
    serializer_class = SyncLogSerializer

    def get_queryset(self):
        accessible = self.request.user.get_accessible_projects()
        job = get_object_or_404(
            SyncJob.objects.filter(site_project__in=accessible),
            pk=self.kwargs["pk"],
        )
        return SyncLog.objects.filter(job=job)


class SyncStatsView(APIView):
    def get(self, request):
        accessible   = request.user.get_accessible_projects()
        jobs         = SyncJob.objects.filter(site_project__in=accessible)
        success_jobs = jobs.filter(status="success")

        return Response({
            "total_jobs":           jobs.count(),
            "success":              success_jobs.count(),
            "failed":               jobs.filter(status="failed").count(),
            "running":              jobs.filter(status="running").count(),
            "pending":              jobs.filter(status="pending").count(),
            "cancelled":            jobs.filter(status="cancelled").count(),
            "total_records_pushed": sum(j.records_pushed for j in success_jobs),
        })