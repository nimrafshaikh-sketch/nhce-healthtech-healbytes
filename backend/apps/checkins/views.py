from django.utils import timezone
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.permissions import IsDoctor, IsPatient

from .models import DailyCheckin
from .serializers import DailyCheckinCreateSerializer, DailyCheckinSerializer
from .tasks import process_checkin_ai_analysis


@extend_schema_view(
    get=extend_schema(tags=["Check-ins"], summary="List check-ins (doctor: own patients, patient: own)"),
    post=extend_schema(tags=["Check-ins"], summary="Submit today's daily check-in (Patient only)"),
)
class CheckinListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), IsPatient()]
        return [permissions.IsAuthenticated(), (IsDoctor | IsPatient)()]

    def get_serializer_class(self):
        return DailyCheckinCreateSerializer if self.request.method == "POST" else DailyCheckinSerializer

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_doctor", False):
            qs = DailyCheckin.objects.filter(patient__doctor=user)
        elif getattr(user, "is_patient", False):
            qs = DailyCheckin.objects.filter(patient__user=user)
        else:
            return DailyCheckin.objects.none()

        patient_id = self.request.query_params.get("patient")
        if patient_id is not None and patient_id != "":
            if not str(patient_id).isdigit():
                return qs.none()
            qs = qs.filter(patient_id=int(patient_id))
        return qs.select_related("patient")

    def perform_create(self, serializer):
        user = self.request.user
        if not getattr(user, "is_patient", False):
            raise PermissionDenied("Only patients can submit check-ins.")
        patient = getattr(user, "patient_profile", None)
        if patient is None:
            raise PermissionDenied("Patient profile not found for this account.")
        checkin_date = serializer.validated_data.get("checkin_date") or timezone.localdate()
        if DailyCheckin.objects.filter(patient=patient, checkin_date=checkin_date).exists():
            raise ValidationError({"checkin_date": "A check-in for this date has already been submitted."})
        checkin = serializer.save(patient=patient, checkin_date=checkin_date)
        process_checkin_ai_analysis.delay(checkin.id)


@extend_schema(tags=["Check-ins"], summary="Retrieve a single check-in")
class CheckinDetailView(generics.RetrieveAPIView):
    serializer_class = DailyCheckinSerializer
    permission_classes = [permissions.IsAuthenticated, (IsDoctor | IsPatient)]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_doctor", False):
            return DailyCheckin.objects.filter(patient__doctor=user)
        if getattr(user, "is_patient", False):
            return DailyCheckin.objects.filter(patient__user=user)
        return DailyCheckin.objects.none()
