from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions

from apps.core.permissions import IsDoctor, IsDoctorOfPatient, IsPatient

from .models import Patient
from .serializers import PatientCreateSerializer, PatientSerializer


@extend_schema_view(
    get=extend_schema(tags=["Patients"], summary="List patients belonging to the logged-in doctor"),
    post=extend_schema(tags=["Patients"], summary="Add a new patient + caretaker details (Doctor only)"),
)
class PatientListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    def get_serializer_class(self):
        return PatientCreateSerializer if self.request.method == "POST" else PatientSerializer

    def get_queryset(self):
        return Patient.objects.filter(doctor=self.request.user.doctor_profile)


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
