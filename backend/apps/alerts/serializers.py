from rest_framework import serializers

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id", "patient", "patient_name", "checkin", "severity", "recipient_role",
            "reason", "status", "acknowledged_by", "acknowledged_at",
            "email_sent", "email_sent_at", "created_at",
        ]
        read_only_fields = fields
