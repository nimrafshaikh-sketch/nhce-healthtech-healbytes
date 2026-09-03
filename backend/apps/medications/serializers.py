from rest_framework import serializers

from .models import Medication, MedicationReminderLog


class MedicationSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)

    class Meta:
        model = Medication
        fields = [
            "id", "patient", "patient_name", "prescribed_by", "name", "dosage",
            "frequency", "instructions", "start_date", "end_date",
            "reminder_times", "reminders_enabled", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "prescribed_by", "created_at", "updated_at"]

    def validate_reminder_times(self, value):
        import re
        pattern = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
        for t in value:
            if not isinstance(t, str) or not pattern.match(t):
                raise serializers.ValidationError(f'"{t}" is not a valid "HH:MM" 24h time.')
        return value

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if end and start and end < start:
            raise serializers.ValidationError("end_date cannot be before start_date.")
        return attrs


class MedicationReminderLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = MedicationReminderLog
        fields = ["id", "medication", "scheduled_for", "sent_at", "acknowledged_at"]
        read_only_fields = fields
