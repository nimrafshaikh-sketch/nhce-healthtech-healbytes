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


def _notify_appointment_created(appointment, *, created_by):
    """Fires the in-app notification for a newly-booked appointment to
    whichever side (doctor and/or patient) didn't just create it themselves -
    e.g. a receptionist booking notifies both; a doctor booking their own
    patient only notifies the patient. Mirrors the create_notification
    pattern used elsewhere (apps.labtests.tasks), but run synchronously since
    it's a single cheap DB write with no external I/O."""
    from apps.notifications.models import Notification
    from apps.notifications.services import create_notification

    when = appointment.scheduled_at.strftime("%b %d, %Y %I:%M %p")

    if appointment.doctor_id != created_by.id:
        create_notification(
            user=appointment.doctor,
            notification_type=Notification.NotificationType.APPOINTMENT,
            title=f"New appointment with {appointment.patient.full_name}",
            body=f"Scheduled for {when}." + (f" Reason: {appointment.reason}" if appointment.reason else ""),
            related_object_type="appointment",
            related_object_id=appointment.id,
        )

    patient_user_id = appointment.patient.user_id
    if patient_user_id and patient_user_id != created_by.id:
        create_notification(
            user=appointment.patient.user,
            notification_type=Notification.NotificationType.APPOINTMENT,
            title="New appointment scheduled",
            body=f"With Dr. {appointment.doctor.get_full_name() or appointment.doctor.email} on {when}.",
            related_object_type="appointment",
            related_object_id=appointment.id,
        )


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
        if patient_id and str(patient_id).isdigit():
            qs = qs.filter(patient_id=int(patient_id))
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
        appointment = serializer.save(created_by=user)
        _notify_appointment_created(appointment, created_by=user)


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
