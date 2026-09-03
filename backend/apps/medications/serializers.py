from rest_framework import serializers

from .models import Medication, MedicationReminder, MedicationAdherence


class MedicationSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)

    class Meta:
        model = Medication
        fields = [
            "id", "patient", "patient_name", "prescribed_by", "medicine_name", "dosage",
            "frequency_per_day", "instructions", "start_date", "end_date",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "prescribed_by", "created_at", "updated_at"]

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if end and start and end < start:
            raise serializers.ValidationError("end_date cannot be before start_date.")
        return attrs


class MedicationReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicationReminder
        fields = ["id", "medication", "reminder_time", "is_active"]
        read_only_fields = ["id"]


class MedicationAdherenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicationAdherence
        fields = ["id", "medication", "patient", "scheduled_time", "taken_at", "status"]
        read_only_fields = ["id", "patient", "scheduled_time"]
