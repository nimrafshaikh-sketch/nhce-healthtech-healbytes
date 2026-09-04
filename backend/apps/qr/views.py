from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.checkins.models import DailyCheckin
from apps.core.permissions import IsDoctor, IsPatient
from apps.medications.models import Medication
from apps.patients.models import Patient
from apps.patients.serializers import PatientSerializer

from .models import QRAccessGrant, QRScanLog
from .serializers import (
    QRGenerateResponseSerializer,
    QRVerifyRequestSerializer,
    QRVerifyResponseSerializer,
)
from .tokens import InvalidQRToken, generate_qr_token, peek_patient_id_for_audit_log, verify_qr_token


@extend_schema(tags=["QR"], summary="Generate a short-lived QR token for the logged-in patient",
               request=None, responses=QRGenerateResponseSerializer)
class QRGenerateView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def post(self, request):
        patient = request.user.patient_profile
        data = generate_qr_token(patient)
        return Response(QRGenerateResponseSerializer(data).data)


@extend_schema(tags=["QR"], summary="Verify a scanned QR token and return authorized patient history "
                                       "(assigned Doctor, or any Doctor presenting a valid signed QR - "
                                       "the latter receives a time-bound consulting access grant, not "
                                       "permanent access; every scan attempt is logged, success or failure)",
               request=QRVerifyRequestSerializer, responses=QRVerifyResponseSerializer)
class QRVerifyView(APIView):
    """Two authorization paths, never opened up to Receptionist/Lab Tech
    (QR is clinical-history access, and Receptionist has zero clinical-data
    access per the locked role matrix; Lab Tech's access is scoped to
    assigned lab work only, not full patient history):

    1. The patient's own assigned doctor: always authorized, no grant needed
       (they already have standing access to everything about this patient).
    2. Any OTHER doctor presenting a genuine, signature-valid, non-expired
       QR token: this is the "multi-doctor consult" path (e.g. the patient
       shows their QR to a new/covering doctor). This is treated as the
       patient's own consent to share their record with that doctor for a
       consultation - but the resulting authorization is a bounded-duration
       QRAccessGrant (see apps.qr.models.QRAccessGrant), NOT permanent
       access, and it never touches `patient.doctor_id` (the patient's
       primary-doctor assignment is completely untouched by QR access).
       All of that doctor's *subsequent* document/RAG access to this
       patient (apps.documents.views) is authorized strictly against this
       grant's expiry, not against the mere existence of a scan log row.

    Every verification attempt is logged via QRScanLog regardless of outcome:
    invalid/expired/malformed token, patient not found, or success.
    Previously the first two cases logged nothing at all - fixed here by
    making QRScanLog.patient nullable (a genuinely undecodable token has no
    knowable patient) and by best-effort recovering the patient from an
    expired-but-genuine token for the log (see tokens.peek_patient_id_for_audit_log).
    """
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def post(self, request):
        serializer = QRVerifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]

        try:
            patient_id = verify_qr_token(token)
        except InvalidQRToken as exc:
            recovered_patient_id = peek_patient_id_for_audit_log(token)
            patient = Patient.objects.filter(id=recovered_patient_id).first() if recovered_patient_id else None
            QRScanLog.objects.create(patient=patient, scanned_by=request.user, success=False,
                                      failure_reason=str(exc))
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            QRScanLog.objects.create(patient=None, scanned_by=request.user, success=False,
                                      failure_reason=f"Patient id {patient_id} not found.")
            return Response({"detail": "Patient not found."}, status=status.HTTP_400_BAD_REQUEST)

        QRScanLog.objects.create(patient=patient, scanned_by=request.user, success=True)

        is_primary_doctor = patient.doctor_id == request.user.id
        if not is_primary_doctor:
            # Multi-doctor consult path: the patient presenting a genuine,
            # signature-valid, non-expired QR to this doctor is treated as
            # consent for a bounded consultation window - never permanent,
            # never a change to patient.doctor_id.
            QRAccessGrant.grant(patient=patient, doctor=request.user)

        from apps.checkins.serializers import DailyCheckinSerializer
        from apps.medications.serializers import MedicationSerializer
        from apps.patients.clinical_brief import build_clinical_brief

        medications = Medication.objects.filter(patient=patient, is_active=True)[:20]
        checkins = DailyCheckin.objects.filter(patient=patient).order_by("-checkin_date")[:14]
        brief_data = build_clinical_brief(patient)

        data = {
            "patient": PatientSerializer(patient).data,
            "recent_medications": MedicationSerializer(medications, many=True).data,
            "recent_checkins": DailyCheckinSerializer(checkins, many=True).data,
            "clinical_brief": brief_data.get("clinical_brief"),
        }
        return Response(data)
