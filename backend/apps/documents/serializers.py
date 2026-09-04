from rest_framework import serializers
from apps.documents.models import MedicalDocument
from apps.patients.models import Patient


class MedicalDocumentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source="patient.full_name", read_only=True)
    uploaded_by_name = serializers.CharField(source="uploaded_by.get_full_name", read_only=True)
    verified_by_name = serializers.CharField(source="verified_by.get_full_name", read_only=True)
    view_url = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    class Meta:
        model = MedicalDocument
        fields = [
            "id", "patient", "patient_name", "uploaded_by", "uploaded_by_name",
            "document_type", "title", "file_type", "file_size",
            "processing_status", "extraction_status", "status",
            "extracted_text", "extracted_data",
            "verified_by", "verified_by_name", "verified_at",
            "view_url", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_view_url(self, obj) -> str:
        return f"/api/documents/{obj.id}/view/"

    def get_status(self, obj) -> str:
        if obj.extraction_status and obj.extraction_status != MedicalDocument.ExtractionStatus.NOT_APPLICABLE:
            return obj.extraction_status
        return obj.processing_status



class MedicalDocumentUploadSerializer(serializers.ModelSerializer):
    patient = serializers.PrimaryKeyRelatedField(queryset=Patient.objects.all(), required=False)
    file = serializers.FileField(required=True)

    class Meta:
        model = MedicalDocument
        fields = ["id", "patient", "document_type", "title", "file"]
        read_only_fields = ["id"]

    def validate_file(self, value):
        # Max file size 15 MB
        max_size = 15 * 1024 * 1024
        if value.size > max_size:
            raise serializers.ValidationError("File size cannot exceed 15 MB.")
        
        # Allowed extensions
        allowed_exts = [".pdf", ".png", ".jpg", ".jpeg", ".txt"]
        ext = value.name.lower().split(".")[-1]
        if f".{ext}" not in allowed_exts:
            raise serializers.ValidationError(f"Unsupported file extension .{ext}. Allowed: {', '.join(allowed_exts)}")
        return value


class PrescriptionVerificationSerializer(serializers.Serializer):
    """Payload when a doctor verifies/approves candidate prescription extraction."""
    name = serializers.CharField(max_length=150)
    dosage = serializers.CharField(max_length=100)
    frequency = serializers.ChoiceField(
        choices=["once_daily", "twice_daily", "three_times_daily", "weekly", "as_needed"],
        default="twice_daily",
    )
    instructions = serializers.CharField(required=False, allow_blank=True, default="")
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False, allow_null=True)
    reminder_times = serializers.ListField(child=serializers.CharField(), required=False, default=list)
