from rest_framework import serializers
from apps.documents.models import MedicalDocument
from apps.documents.ocr import _IMAGE_SIGNATURES
from apps.patients.models import Patient

# Real file-content signatures ("magic bytes") the allowed extensions must
# actually match - closes the gap where a file's claimed extension was the
# only thing validated (HealBytes_Independent_Verification_Report.md, §10
# item 9: a PE executable renamed to .txt was accepted). PNG/JPEG reuse the
# same signatures apps.documents.ocr already sniffs images by, so there is
# one source of truth for "what a real PNG/JPEG looks like".
_EXTENSION_SIGNATURES = {
    "pdf": (b"%PDF",),
    "png": tuple(sig for sig, fmt in _IMAGE_SIGNATURES if fmt == "PNG"),
    "jpg": tuple(sig for sig, fmt in _IMAGE_SIGNATURES if fmt == "JPEG"),
    "jpeg": tuple(sig for sig, fmt in _IMAGE_SIGNATURES if fmt == "JPEG"),
    # .txt has no fixed structural signature (it's free text) - handled by
    # the dangerous-signature check below instead of a positive match.
}

# Executable/binary signatures that must never be accepted under any allowed
# extension, regardless of what the filename claims.
_DANGEROUS_SIGNATURES = (
    (b"MZ", "a Windows/DOS executable (PE)"),
    (b"\x7fELF", "a Linux executable (ELF)"),
    (b"\xca\xfe\xba\xbe", "a Mach-O/Java fat binary"),
    (b"\xfe\xed\xfa", "a Mach-O executable"),
    (b"PK\x03\x04", "a ZIP/Office archive"),
)


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

        # Content-based validation: the claimed extension must match the
        # file's real binary signature, and no upload may carry a known
        # executable/archive signature regardless of extension. A mislabeled
        # or spoofed extension no longer bypasses this (previously
        # extension-only - see _DANGEROUS_SIGNATURES/_EXTENSION_SIGNATURES
        # above for the specific gap this closes).
        try:
            value.seek(0)
            head = value.read(16)
            value.seek(0)
        except Exception:
            raise serializers.ValidationError("Unable to read file content for validation.")

        for signature, label in _DANGEROUS_SIGNATURES:
            if head.startswith(signature):
                raise serializers.ValidationError(
                    f"File content does not match an allowed medical document format (detected {label})."
                )

        expected_signatures = _EXTENSION_SIGNATURES.get(ext)
        if expected_signatures and not any(head.startswith(sig) for sig in expected_signatures):
            raise serializers.ValidationError(
                f"File content does not match its .{ext} extension. Upload rejected."
            )

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
