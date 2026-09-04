from rest_framework import serializers

from .models import Alert


class AlertSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.name", read_only=True)

    class Meta:
        model = Alert
        fields = [
            "id", "patient", "patient_name", "checkin", "risk_level", "recipient_type",
            "reason", "status", "resolved_at", 
            "created_at",
        ]
        read_only_fields = fields
