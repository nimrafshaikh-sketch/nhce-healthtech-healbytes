from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .serializers import (
    ChangePasswordSerializer,
    DetailResponseSerializer,
    DoctorRegisterSerializer,
    EmailTokenObtainPairSerializer,
    UserSerializer,
)

User = get_user_model()


@extend_schema(tags=["Auth"], summary="Register a new Doctor account")
class DoctorRegisterView(generics.CreateAPIView):
    """Doctors self-register. Patients do NOT use this endpoint -
    patient accounts are created via invitation-code redemption
    (see /api/invitations/redeem/)."""
    queryset = User.objects.all()
    serializer_class = DoctorRegisterSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(tags=["Auth"], summary="List available doctors")
class DoctorListView(generics.ListAPIView):
    queryset = User.objects.filter(role=User.Role.DOCTOR, is_active=True)
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]


@extend_schema(tags=["Auth"], summary="Login (obtain JWT access/refresh pair)")
class LoginView(TokenObtainPairView):
    serializer_class = EmailTokenObtainPairSerializer
    permission_classes = [permissions.AllowAny]


@extend_schema(tags=["Auth"], summary="Refresh JWT access token")
class RefreshView(TokenRefreshView):
    permission_classes = [permissions.AllowAny]


@extend_schema(tags=["Auth"], summary="Get or update the current user's profile")
class MeView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


@extend_schema(tags=["Auth"], summary="Change the current user's password",
               request=ChangePasswordSerializer, responses=DetailResponseSerializer)
class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = request.user
        if not user.check_password(serializer.validated_data["old_password"]):
            return Response({"detail": "Old password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response({"detail": "Password updated."})
