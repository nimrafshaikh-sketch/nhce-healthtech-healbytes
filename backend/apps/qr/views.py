from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.checkins.models import DailyCheckin
from apps.core.permissions import IsDoctor, IsPatient
from apps.medications.models import Medication
from apps.patients.models import Patient
from apps.patients.serializers import PatientSerializer

from .models import QRAccess
from .serializers import (
    QRGenerateResponseSerializer,
    QRVerifyRequestSerializer,
    QRVerifyResponseSerializer,
)
from .tokens import InvalidQRToken, generate_qr_token, verify_qr_token


@extend_schema(tags=["QR"], summary="Generate a short-lived QR token for the logged-in patient",
               request=None, responses=QRGenerateResponseSerializer)
class QRGenerateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def post(self, request):
        patient = request.user.patient_profile
        data = generate_qr_token(patient)
        return Response(QRGenerateResponseSerializer(data).data)


@extend_schema(tags=["QR"], summary="Verify a scanned QR token and return authorized patient history (Doctor only)",
               request=QRVerifyRequestSerializer, responses=QRVerifyResponseSerializer)
class QRVerifyView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def post(self, request):
        serializer = QRVerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        try:
            qr_access = verify_qr_token(token)
            patient = qr_access.patient
        except InvalidQRToken as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        if patient.doctor_id != request.user.id:
            qr_access.access_status = QRAccess.AccessStatus.DENIED
            qr_access.accessed_by = getattr(request.user, "email", str(request.user))
            qr_access.save(update_fields=["access_status", "accessed_by"])
            return Response({"detail": "You are not the assigned doctor for this patient."},
                             status=status.HTTP_403_FORBIDDEN)

        from django.utils import timezone
        qr_access.access_status = QRAccess.AccessStatus.GRANTED
        qr_access.accessed_by = getattr(request.user, "email", str(request.user))
        qr_access.used_at = timezone.now()
        qr_access.save(update_fields=["access_status", "accessed_by", "used_at"])

        from apps.checkins.serializers import DailyCheckinSerializer
        from apps.medications.serializers import MedicationSerializer

        medications = Medication.objects.filter(patient=patient, end_date__isnull=True)[:20]
        checkins = DailyCheckin.objects.filter(patient=patient).order_by("-checkin_date")[:14]

        data = {
            "patient": PatientSerializer(patient).data,
            "recent_medications": MedicationSerializer(medications, many=True).data,
            "recent_checkins": DailyCheckinSerializer(checkins, many=True).data,
        }
        return Response(data)
