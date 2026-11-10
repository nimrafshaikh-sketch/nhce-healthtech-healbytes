from rest_framework import serializers

from .models import DailyCheckin


class DailyCheckinSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)

    class Meta:
        model = DailyCheckin
        fields = [
            "id", "patient", "patient_name", "checkin_date", "symptoms", "mood",
            "pain_level", "symptom_duration", "medication_adherence",
            "notes", "vitals", "ai_risk_level", "ai_risk_score", "ai_notes",
            "ai_recommended_action", "ai_notification_recipient", "ai_processed_at", "created_at",
        ]
        read_only_fields = [
            "id", "patient", "ai_risk_level", "ai_risk_score", "ai_notes",
            "ai_recommended_action", "ai_notification_recipient", "ai_processed_at", "created_at",
        ]


class DailyCheckinCreateSerializer(serializers.ModelSerializer):
    duration = serializers.CharField(max_length=30, required=False, allow_blank=True, write_only=True)

    class Meta:
        model = DailyCheckin
        fields = [
            "id", "checkin_date", "symptoms", "mood", "pain_level",
            "duration", "symptom_duration", "medication_adherence",
            "notes", "vitals", "ai_risk_level", "created_at",
        ]
        read_only_fields = ["id", "ai_risk_level", "created_at"]

    def create(self, validated_data):
        duration = validated_data.pop("duration", None)
        if duration and not validated_data.get("symptom_duration"):
            validated_data["symptom_duration"] = duration
        return super().create(validated_data)
