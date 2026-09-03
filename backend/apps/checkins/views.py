from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions
from rest_framework.exceptions import PermissionDenied

from apps.core.permissions import IsDoctor, IsPatient

from .models import DailyCheckin
from .serializers import DailyCheckinCreateSerializer, DailyCheckinSerializer
from .tasks import process_checkin_ai_analysis


@extend_schema_view(
    get=extend_schema(tags=["Check-ins"], summary="List check-ins (doctor: own patients, patient: own)"),
    post=extend_schema(tags=["Check-ins"], summary="Submit today's daily check-in (Patient only)"),
)
class CheckinListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        return DailyCheckinCreateSerializer if self.request.method == "POST" else DailyCheckinSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_doctor:
            qs = DailyCheckin.objects.filter(patient__doctor=user)
        else:
            qs = DailyCheckin.objects.filter(patient__user=user)
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        return qs.select_related("patient")

    def perform_create(self, serializer):
        from rest_framework.exceptions import ValidationError

        from .models import DailyCheckin

        user = self.request.user
        if not user.is_patient:
            raise PermissionDenied("Only patients can submit check-ins.")
        patient = user.patient_profile
        checkin_date = serializer.validated_data.get("checkin_date")
        if DailyCheckin.objects.filter(patient=patient, checkin_date=checkin_date).exists():
            raise ValidationError({"checkin_date": "A check-in for this date has already been submitted."})
        checkin = serializer.save(patient=patient)
        process_checkin_ai_analysis.delay(checkin.id)


@extend_schema(tags=["Check-ins"], summary="Retrieve a single check-in")
class CheckinDetailView(generics.RetrieveAPIView):
    serializer_class = DailyCheckinSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_doctor:
            return DailyCheckin.objects.filter(patient__doctor=user)
        return DailyCheckin.objects.filter(patient__user=user)
