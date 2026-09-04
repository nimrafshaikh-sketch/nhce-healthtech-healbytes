from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsDoctor, IsDoctorOfPatient, IsPatient
from apps.patients.models import Patient
from apps.qr.models import QRAccessGrant

from .intelligence import analyze_patient_medications
from .models import Medication, MedicationReminderLog, Prescription
from .serializers import MedicationReminderLogSerializer, MedicationSerializer, PrescriptionSerializer


@extend_schema_view(
    get=extend_schema(tags=["Medications"], summary="List medications (doctor: own patients, patient: own)"),
    post=extend_schema(tags=["Medications"], summary="Add a medication for a patient (Doctor only)"),
)
class MedicationListCreateView(generics.ListCreateAPIView):
    serializer_class = MedicationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_doctor:
            qs = Medication.objects.filter(patient__doctor=user)
        else:
            qs = Medication.objects.filter(patient__user=user)
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        return qs.select_related("patient")

    def perform_create(self, serializer):
        if not self.request.user.is_doctor:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only doctors can prescribe medications.")
        patient = Patient.objects.get(id=self.request.data.get("patient"), doctor=self.request.user)
        serializer.save(prescribed_by=self.request.user, patient=patient)


@extend_schema(tags=["Medications"], summary="Retrieve/update/delete a medication (Doctor only, own patients)")
class MedicationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MedicationSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor, IsDoctorOfPatient]
    queryset = Medication.objects.all()


@extend_schema(tags=["Medications"], summary="List reminder-dispatch history for a medication")
class MedicationReminderLogListView(generics.ListAPIView):
    serializer_class = MedicationReminderLogSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base = MedicationReminderLog.objects.filter(medication_id=self.kwargs["medication_id"])
        if user.is_doctor:
            return base.filter(medication__patient__doctor=user)
        return base.filter(medication__patient__user=user)


@extend_schema(tags=["Medications"], summary="Patient acknowledges a dispatched reminder", request=None, responses=MedicationReminderLogSerializer)
class AcknowledgeReminderView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def post(self, request, pk):
        from django.utils import timezone
        log = generics.get_object_or_404(
            MedicationReminderLog, pk=pk, medication__patient__user=request.user
        )
        log.acknowledged_at = timezone.now()
        log.save(update_fields=["acknowledged_at"])
        return Response(MedicationReminderLogSerializer(log).data)


@extend_schema_view(
    get=extend_schema(tags=["Prescriptions"], summary="List prescriptions (doctor: own patients, patient: own)"),
    post=extend_schema(tags=["Prescriptions"], summary="Add a prescription for a patient (Doctor only)"),
)
class PrescriptionListCreateView(generics.ListCreateAPIView):
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_doctor:
            from apps.qr.models import QRAccessGrant
            from django.db.models import Q
            from django.utils import timezone
            
            # Allow assigned patients OR patients for which doctor has an active QR grant
            active_grants = QRAccessGrant.objects.filter(doctor=user, expires_at__gte=timezone.now())
            grant_patient_ids = active_grants.values_list('patient_id', flat=True)
            
            qs = Prescription.objects.filter(
                Q(patient__doctor=user) | Q(patient_id__in=grant_patient_ids)
            )
        else:
            qs = Prescription.objects.filter(patient__user=user)
            
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        return qs.select_related("patient", "doctor")

    def perform_create(self, serializer):
        if not self.request.user.is_doctor:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Only doctors can prescribe medications.")
        
        # When creating, only allow creating for own assigned patients, or if there's a QR grant.
        patient_id = self.request.data.get("patient")
        try:
            patient = Patient.objects.get(id=patient_id)
        except Patient.DoesNotExist:
            from rest_framework.exceptions import NotFound
            raise NotFound("Patient not found.")
            
        if patient.doctor != self.request.user:
            from apps.qr.models import QRAccessGrant
            if not QRAccessGrant.has_active_grant(patient=patient, doctor=self.request.user):
                from rest_framework.exceptions import PermissionDenied
                raise PermissionDenied("You do not have access to this patient.")
                
        serializer.save(doctor=self.request.user, patient=patient)


@extend_schema(tags=["Prescriptions"], summary="Retrieve/update/delete a prescription (Doctor only, allowed patients)")
class PrescriptionDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PrescriptionSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor]
    
    def get_queryset(self):
        user = self.request.user
        from apps.qr.models import QRAccessGrant
        from django.db.models import Q
        from django.utils import timezone
        
        active_grants = QRAccessGrant.objects.filter(doctor=user, expires_at__gte=timezone.now())
        grant_patient_ids = active_grants.values_list('patient_id', flat=True)
        
        return Prescription.objects.filter(
            Q(patient__doctor=user) | Q(patient_id__in=grant_patient_ids)
        )

@extend_schema(tags=["Medications"], summary="Medication Intelligence: deterministic reconciliation of current/historical/document-derived medication data (read-only)")
class MedicationIntelligenceView(APIView):
    """Phase 3 - reconciles the authoritative Medication table against
    document-derived candidate prescriptions and surfaces structured
    observations (duplicates, conflicting dosage, regimen changes,
    document-vs-record discrepancies, incomplete extractions).

    Deterministic, no LLM. Read-only: never creates, updates, or deletes a
    Medication record - see apps.medications.intelligence module docstring.

    Authorization mirrors DocumentRAGSearchView: the assigned doctor, a
    doctor with an active QRAccessGrant for this patient, or the patient
    themselves. Everyone else is denied.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        patient_id = request.query_params.get("patient_id") or request.query_params.get("patient")
        if not patient_id:
            return Response({"detail": "patient_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        patient = generics.get_object_or_404(Patient, pk=patient_id)
        user = request.user

        if getattr(user, "is_doctor", False):
            if patient.doctor_id != user.id:
                if not QRAccessGrant.has_active_grant(patient=patient, doctor=user):
                    raise PermissionDenied("You are not authorized to view this patient's medication intelligence.")
        elif getattr(user, "is_patient", False):
            if not hasattr(user, "patient_profile") or user.patient_profile.id != patient.id:
                raise PermissionDenied("You cannot access another patient's medication intelligence.")
        else:
            raise PermissionDenied("Non-clinical staff cannot access medication intelligence.")

        return Response(analyze_patient_medications(patient.id), status=status.HTTP_200_OK)
