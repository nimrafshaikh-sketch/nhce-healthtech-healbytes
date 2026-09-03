from rest_framework import serializers

from apps.checkins.serializers import DailyCheckinSerializer
from apps.medications.serializers import MedicationSerializer
from apps.patients.serializers import PatientSerializer


class QRGenerateResponseSerializer(serializers.Serializer):
    token = serializers.CharField()
    expires_at = serializers.DateTimeField()


class QRVerifyRequestSerializer(serializers.Serializer):
    token = serializers.CharField()


class QRVerifyResponseSerializer(serializers.Serializer):
    patient = PatientSerializer()
    recent_medications = MedicationSerializer(many=True)
    recent_checkins = DailyCheckinSerializer(many=True)
