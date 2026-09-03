from rest_framework import serializers

from apps.accounts.models import User

from .models import Appointment


class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    doctor_name = serializers.CharField(source="doctor.get_full_name", read_only=True)

    class Meta:
        model = Appointment
        fields = [
            "id", "patient", "patient_name", "doctor", "doctor_name", "created_by",
            "scheduled_at", "duration_minutes", "reason", "status", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_by", "status", "created_at", "updated_at"]


class AppointmentWriteSerializer(serializers.ModelSerializer):
    """Used for both create (Doctor: own patients / Receptionist: any) and
    update/reschedule - see apps.appointments.views for who's allowed which.
    """
    doctor = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(role=User.Role.DOCTOR))

    class Meta:
        model = Appointment
        # Doctor/Receptionist can set any status via this field (e.g. mark
        # completed/no_show/cancelled). Patient never uses this serializer -
        # see AppointmentConfirmView/AppointmentCancelView instead.
        fields = ["id", "patient", "doctor", "scheduled_at", "duration_minutes", "reason", "notes", "status"]
        read_only_fields = ["id"]
