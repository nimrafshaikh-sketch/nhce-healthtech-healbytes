from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema, extend_schema_view
from rest_framework import generics, permissions
from rest_framework.exceptions import ValidationError

from apps.core.permissions import IsDoctor, IsDoctorOfPatient, IsPatient, IsReceptionist

from .models import Patient
from .serializers import (
    AdministrativePatientSerializer,
    PatientCreateSerializer,
    PatientSerializer,
    ReceptionistPatientCreateSerializer,
)


@extend_schema_view(
    get=extend_schema(tags=["Patients"], summary="List patients belonging to the logged-in doctor"),
    post=extend_schema(tags=["Patients"], summary="Add a new patient + caretaker details "
                                                     "(Doctor: self, or Receptionist: picks a doctor)"),
)
class PatientListCreateView(generics.ListCreateAPIView):
    """GET stays doctor-only (own patients) - receptionist has no bare
    "list all patients" here, per the non-enumeration principle; they use
    PatientSearchView instead. POST is open to both Doctor and Receptionist,
    with a different serializer per role (see get_serializer_class)."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), (IsDoctor | IsReceptionist)()]
        return [permissions.IsAuthenticated(), IsDoctor()]

    def get_serializer_class(self):
        if self.request.method != "POST":
            return PatientSerializer
        # getattr guard: AnonymousUser (schema generation, unauthenticated
        # requests before permission checks run) has no is_receptionist.
        if getattr(self.request.user, "is_receptionist", False):
            return ReceptionistPatientCreateSerializer
        return PatientCreateSerializer

    def get_queryset(self):
        return Patient.objects.filter(doctor=self.request.user)


@extend_schema(tags=["Patients"], summary="Retrieve/update/delete a single patient (Doctor only, own patients)")
class PatientDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated, IsDoctor, IsDoctorOfPatient]
    queryset = Patient.objects.all()


@extend_schema(tags=["Patients"], summary="Get the logged-in patient's own profile")
class MyPatientProfileView(generics.RetrieveAPIView):
    serializer_class = PatientSerializer
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def get_object(self):
        return get_object_or_404(Patient, user=self.request.user)


@extend_schema(
    tags=["Patients"],
    summary="Receptionist: search patients by phone number, or by name + date of birth",
    description="Requires either `phone_number`, or both `name` and `date_of_birth` - "
                 "there is no unfiltered listing, to avoid enumerating the full patient roster. "
                 "Cross-doctor (reception serves the whole clinic). Excludes medical_notes.",
    parameters=[
        OpenApiParameter("phone_number", str, required=False),
        OpenApiParameter("name", str, required=False),
        OpenApiParameter("date_of_birth", str, required=False, description="YYYY-MM-DD"),
    ],
    responses=AdministrativePatientSerializer,
)
class PatientSearchView(generics.ListAPIView):
    serializer_class = AdministrativePatientSerializer
    permission_classes = [permissions.IsAuthenticated, IsReceptionist]

    def get_queryset(self):
        phone_number = self.request.query_params.get("phone_number", "").strip()
        name = self.request.query_params.get("name", "").strip()
        date_of_birth = self.request.query_params.get("date_of_birth", "").strip()

        if phone_number:
            return Patient.objects.filter(phone_number__icontains=phone_number)
        if name and date_of_birth:
            return Patient.objects.filter(full_name__icontains=name, date_of_birth=date_of_birth)
        raise ValidationError(
            "Provide either 'phone_number', or both 'name' and 'date_of_birth' to search."
        )
