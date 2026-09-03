from rest_framework.permissions import BasePermission


class IsAppointmentDoctor(BasePermission):
    """Object-level check: the requesting doctor must be the doctor on
    THIS appointment (Appointment.doctor, not necessarily the patient's
    overall assigned doctor - a receptionist can book a patient with a
    covering doctor)."""
    message = "You are not the doctor on this appointment."

    def has_object_permission(self, request, view, obj):
        return obj.doctor_id == request.user.id
