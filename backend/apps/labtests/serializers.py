from rest_framework import serializers

from .models import LabTestRequest, LabTestResult


class LabTestResultSerializer(serializers.ModelSerializer):
    recorded_by_name = serializers.CharField(source="recorded_by.get_full_name", read_only=True)
    reviewed_by_name = serializers.CharField(source="reviewed_by.get_full_name", read_only=True)

    class Meta:
        model = LabTestResult
        fields = [
            "id", "request", "recorded_by", "recorded_by_name", "result_text", "notes",
            "reviewed_by", "reviewed_by_name", "reviewed_at", "created_at",
        ]
        read_only_fields = ["id", "request", "recorded_by", "reviewed_by", "reviewed_at", "created_at"]


class LabTestResultCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTestResult
        fields = ["id", "result_text", "notes"]
        read_only_fields = ["id"]


class LabTestRequestSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    requested_by_name = serializers.CharField(source="requested_by.get_full_name", read_only=True)
    assigned_lab_tech_name = serializers.CharField(source="assigned_lab_tech.get_full_name", read_only=True)
    result = LabTestResultSerializer(read_only=True)

    class Meta:
        model = LabTestRequest
        fields = [
            "id", "patient", "patient_name", "requested_by", "requested_by_name",
            "assigned_lab_tech", "assigned_lab_tech_name", "test_name", "priority",
            "status", "notes", "result", "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "requested_by", "assigned_lab_tech", "status", "result", "created_at", "updated_at",
        ]


class LabTestRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LabTestRequest
        fields = ["id", "patient", "test_name", "priority", "notes", "status", "assigned_lab_tech"]
        read_only_fields = ["id", "status", "assigned_lab_tech"]
