from rest_framework import serializers

from .models import DailyCheckin


class DailyCheckinSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)

    class Meta:
        model = DailyCheckin
        fields = [
            "id", "patient", "patient_name", "checkin_date", "symptoms", "mood",
            "pain_level", "notes", "vitals", "ai_risk_level", "ai_risk_score", "ai_notes",
            "ai_recommended_action", "ai_notification_recipient", "ai_processed_at", "created_at",
        ]
        read_only_fields = [
            "id", "patient", "ai_risk_level", "ai_risk_score", "ai_notes",
            "ai_recommended_action", "ai_notification_recipient", "ai_processed_at", "created_at",
        ]


class DailyCheckinCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyCheckin
        fields = ["id", "checkin_date", "symptoms", "mood", "pain_level", "notes", "vitals"]
        read_only_fields = ["id"]
