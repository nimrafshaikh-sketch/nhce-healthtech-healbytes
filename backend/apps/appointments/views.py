from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema, extend_schema_view
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsDoctor, IsPatient, IsReceptionist, IsSelfPatient

from .models import Appointment
from .permissions import IsAppointmentDoctor
from .serializers import AppointmentSerializer, AppointmentWriteSerializer


@extend_schema_view(
    get=extend_schema(tags=["Appointments"], summary="List appointments (Doctor: own, Receptionist: all, "
                                                        "Patient: own)"),
    post=extend_schema(tags=["Appointments"], summary="Book an appointment (Doctor: own patients only, "
                                                         "Receptionist: any patient/doctor)"),
)
class AppointmentListCreateView(generics.ListCreateAPIView):
    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated(), (IsDoctor | IsReceptionist)()]
        return [permissions.IsAuthenticated(), (IsDoctor | IsReceptionist | IsPatient)()]

    def get_serializer_class(self):
        return AppointmentWriteSerializer if self.request.method == "POST" else AppointmentSerializer

    def get_queryset(self):
        user = self.request.user
        qs = Appointment.objects.select_related("patient", "doctor")
        if user.is_doctor:
            qs = qs.filter(doctor=user)
        elif user.is_patient:
            qs = qs.filter(patient__user=user)
        # receptionist: unfiltered (serves the whole clinic)
        patient_id = self.request.query_params.get("patient")
        if patient_id:
            qs = qs.filter(patient_id=patient_id)
        return qs

    def perform_create(self, serializer):
        user = self.request.user
        if user.is_doctor:
            patient = serializer.validated_data["patient"]
            if patient.doctor_id != user.id:
                raise PermissionDenied("You can only book appointments for your own patients.")
            if serializer.validated_data["doctor"].id != user.id:
                raise ValidationError({"doctor": "Doctors can only book appointments with themselves."})
        # receptionist: no restriction - any patient/doctor combination
        serializer.save(created_by=user)


@extend_schema(tags=["Appointments"], summary="Retrieve/reschedule/update status of an appointment "
                                                "(Doctor: own appointments, Receptionist: any, "
                                                "Patient: read-only own)")
class AppointmentDetailView(generics.RetrieveUpdateAPIView):
    queryset = Appointment.objects.select_related("patient", "doctor")

    def get_serializer_class(self):
        return AppointmentSerializer if self.request.method == "GET" else AppointmentWriteSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [
                permissions.IsAuthenticated(),
                ((IsDoctor & IsAppointmentDoctor) | IsReceptionist | (IsPatient & IsSelfPatient))(),
            ]
        return [permissions.IsAuthenticated(), ((IsDoctor & IsAppointmentDoctor) | IsReceptionist)()]


@extend_schema(tags=["Appointments"], summary="Patient confirms their own scheduled appointment",
               request=None, responses=AppointmentSerializer)
class AppointmentConfirmView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk, patient__user=request.user)
        if appointment.status != Appointment.Status.SCHEDULED:
            return Response(
                {"detail": f"Cannot confirm an appointment with status '{appointment.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.status = Appointment.Status.CONFIRMED
        appointment.save(update_fields=["status"])
        return Response(AppointmentSerializer(appointment).data)


@extend_schema(tags=["Appointments"], summary="Patient cancels their own appointment",
               request=None, responses=AppointmentSerializer)
class AppointmentCancelView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsPatient]

    def post(self, request, pk):
        appointment = get_object_or_404(Appointment, pk=pk, patient__user=request.user)
        if appointment.status not in (Appointment.Status.SCHEDULED, Appointment.Status.CONFIRMED):
            return Response(
                {"detail": f"Cannot cancel an appointment with status '{appointment.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        appointment.status = Appointment.Status.CANCELLED
        appointment.save(update_fields=["status"])
        return Response(AppointmentSerializer(appointment).data)
