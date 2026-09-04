from rest_framework import serializers

from .models import EmailNotificationLog, Notification


class NotificationSerializer(serializers.ModelSerializer):
    is_read = serializers.BooleanField(read_only=True)

    class Meta:
        model = Notification
        fields = [
            "id", "notification_type", "title", "body", "related_object_type",
            "related_object_id", "is_read", "read_at", "created_at",
        ]
        read_only_fields = fields


class EmailNotificationLogSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)

    class Meta:
        model = EmailNotificationLog
        fields = [
            "id", "recipient_type", "recipient_email", "category", "patient", "patient_name",
            "checkin", "alert", "medication", "lab_test_request", "subject", "risk_level",
            "sent", "error", "created_at",
        ]
        read_only_fields = fields
