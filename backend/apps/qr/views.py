from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.checkins.models import DailyCheckin
from apps.core.permissions import IsDoctor, IsPatient
from apps.medications.models import Medication
from apps.patients.models import Patient
from apps.patients.serializers import PatientSerializer

from .models import QRScanLog
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
            patient_id = verify_qr_token(token)
        except InvalidQRToken as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            # Nothing valid to attach the log to (token referenced a patient
            # that no longer exists) - just refuse, don't log.
            return Response({"detail": "Patient not found."}, status=status.HTTP_400_BAD_REQUEST)

        if patient.doctor_id != request.user.id:
            QRScanLog.objects.create(patient=patient, scanned_by=request.user, success=False,
                                      failure_reason="Doctor is not assigned to this patient.")
            return Response({"detail": "You are not the assigned doctor for this patient."},
                             status=status.HTTP_403_FORBIDDEN)

        QRScanLog.objects.create(patient=patient, scanned_by=request.user, success=True)

        from apps.checkins.serializers import DailyCheckinSerializer
        from apps.medications.serializers import MedicationSerializer

        medications = Medication.objects.filter(patient=patient, is_active=True)[:20]
        checkins = DailyCheckin.objects.filter(patient=patient).order_by("-checkin_date")[:14]

        data = {
            "patient": PatientSerializer(patient).data,
            "recent_medications": MedicationSerializer(medications, many=True).data,
            "recent_checkins": DailyCheckinSerializer(checkins, many=True).data,
        }
        return Response(data)
