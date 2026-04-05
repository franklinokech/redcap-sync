# apps/accounts/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import User
from .serializers import UserSerializer, UserCreateSerializer, ChangePasswordSerializer


class MeView(APIView):
    """Get or update the currently authenticated user."""

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ChangePasswordView(APIView):
    """Change password for the currently authenticated user."""

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
        user.save()
        return Response({"detail": "Password changed successfully."})


class UserListView(generics.ListCreateAPIView):
    """List all users or create a new one. Admin only."""
    serializer_class = UserCreateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if self.request.user.is_admin or self.request.user.is_superuser:
            return User.objects.all()
        return User.objects.filter(pk=self.request.user.pk)

    def get_serializer_class(self):
        if self.request.method == "GET":
            return UserSerializer
        return UserCreateSerializer

    def perform_create(self, serializer):
        if not (self.request.user.is_admin or self.request.user.is_superuser):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only admins can create users.")
        serializer.save()


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Get, update, or delete a specific user. Admin only."""
    serializer_class = UserSerializer
    queryset         = User.objects.all()

    def get_permissions(self):
        return [permissions.IsAuthenticated()]

    def get_object(self):
        obj = super().get_object()
        if not (self.request.user.is_admin or self.request.user.pk == obj.pk):
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("You do not have permission to access this user.")
        return obj