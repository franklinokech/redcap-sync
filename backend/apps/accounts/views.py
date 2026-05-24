# apps/accounts/views.py
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import User
from .serializers import ChangePasswordSerializer, UserCreateSerializer, UserSerializer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_privileged(user) -> bool:
    """True if the user has admin role OR Django superuser flag."""
    return user.is_superuser or user.role == User.Role.ADMIN


# ---------------------------------------------------------------------------
# /api/accounts/me/
# ---------------------------------------------------------------------------

class MeView(APIView):
    """
    GET   /api/accounts/me/   -- authenticated user's full profile
    PATCH /api/accounts/me/   -- self-update (safe fields only)

    Fields the user may self-edit: first_name, last_name, email, organisation.
    Attempts to escalate role / is_staff / is_superuser are silently dropped.
    """
    permission_classes = [permissions.IsAuthenticated]

    # Fields a user is allowed to update on their own profile.
    _SELF_EDITABLE = {"first_name", "last_name", "email", "organisation"}

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        # Strip anything outside the allow-list before it reaches the serializer
        safe_data = {
            k: v for k, v in request.data.items()
            if k in self._SELF_EDITABLE
        }
        serializer = UserSerializer(
            request.user,
            data=safe_data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


# ---------------------------------------------------------------------------
# /api/accounts/me/change-password/
# ---------------------------------------------------------------------------

class ChangePasswordView(APIView):
    """
    POST /api/accounts/me/change-password/
    Body: { old_password, new_password }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response(
                {"old_password": "Incorrect password."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.validated_data["new_password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password changed successfully."})


# ---------------------------------------------------------------------------
# /api/accounts/users/
# ---------------------------------------------------------------------------

class UserListView(generics.ListCreateAPIView):
    """
    GET  /api/accounts/users/  -- list users
    POST /api/accounts/users/  -- create a new user (admin only)

    Non-admin authenticated users see only their own record.
    Admins see all users.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if _is_privileged(self.request.user):
            return User.objects.all().order_by("username")
        # Non-admins can only see themselves
        return User.objects.filter(pk=self.request.user.pk)

    def get_serializer_class(self):
        if self.request.method == "POST":
            return UserCreateSerializer
        return UserSerializer

    def perform_create(self, serializer):
        if not _is_privileged(self.request.user):
            raise PermissionDenied("Only admins can create users.")
        serializer.save()


# ---------------------------------------------------------------------------
# /api/accounts/users/<pk>/
# ---------------------------------------------------------------------------

class UserDetailView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/accounts/users/<pk>/  -- fetch a user record
    PATCH /api/accounts/users/<pk>/  -- update a user record

    Rules:
      - Any authenticated user may GET/PATCH their own record.
      - Admins may GET/PATCH any record.
      - Non-admins attempting to access another user's record get 403.
      - DELETE is intentionally disabled; deactivate via PATCH is_active=false.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class   = UserSerializer
    queryset           = User.objects.all()
    http_method_names  = ["get", "patch", "head", "options"]  # no PUT, no DELETE

    def get_object(self):
        obj = super().get_object()
        if not (_is_privileged(self.request.user) or self.request.user.pk == obj.pk):
            raise PermissionDenied(
                "You do not have permission to access this user."
            )
        return obj

    def partial_update(self, request, *args, **kwargs):
        # Non-admins updating their own record: restrict to safe fields only
        if not _is_privileged(request.user):
            safe_data = {
                k: v for k, v in request.data.items()
                if k in MeView._SELF_EDITABLE
            }
            kwargs["partial"] = True
            serializer = self.get_serializer(
                self.get_object(), data=safe_data, partial=True
            )
            serializer.is_valid(raise_exception=True)
            serializer.save()
            return Response(serializer.data)
        return super().partial_update(request, *args, **kwargs)
