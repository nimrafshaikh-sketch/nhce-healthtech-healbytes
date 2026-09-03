from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsDoctor, IsDoctorOfPatient, IsPatient
from apps.patients.models import Patient

from .models import Medication, MedicationAdherence
from .serializers import MedicationAdherenceSerializer, MedicationSerializer


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
        patient = Patient.objects.get(id=self.request.data.get("patient"), doctor=self.request.user.doctor_profile)
        serializer.save(prescribed_by=self.request.user, patient=patient)


@extend_schema(tags=["Medications"], summary="Retrieve/update/delete a medication (Doctor only, own patients)")
class MedicationDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = MedicationSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor, IsDoctorOfPatient]
    queryset = Medication.objects.all()


@extend_schema(tags=["Medications"], summary="List adherence logs for a medication")
class MedicationAdherenceListView(generics.ListAPIView):
    serializer_class = MedicationAdherenceSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        base = MedicationAdherence.objects.filter(medication_id=self.kwargs["medication_id"])
        if user.is_doctor:
            return base.filter(medication__patient__doctor=user)
        return base.filter(medication__patient__user=user)


@extend_schema(tags=["Medications"], summary="Patient marks a medication as taken/missed", request=None, responses=MedicationAdherenceSerializer)
class UpdateAdherenceView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def post(self, request, pk):
        from django.utils import timezone
        status = request.data.get("status", "TAKEN")
        log = generics.get_object_or_404(
            MedicationAdherence, pk=pk, medication__patient__user=request.user
        )
        log.status = status
        if status == "TAKEN":
            log.taken_at = timezone.now()
        log.save(update_fields=["status", "taken_at"])
        return Response(MedicationAdherenceSerializer(log).data)
