import os
import uuid
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


def document_file_path(instance, filename):
    """Generate a safe randomized storage path to prevent directory traversal and collisions."""
    ext = os.path.splitext(filename)[1].lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    patient_id = instance.patient_id if instance.patient_id else "unassigned"
    return os.path.join("protected_documents", f"patient_{patient_id}", unique_name)


class MedicalDocument(TimeStampedModel):
    """Authoritative source medical document uploaded for a patient.
    Supports PDFs, images, and clinical scans with OCR extraction, provenance,
    and patient-scoped RAG indexing.
    """

    class DocumentType(models.TextChoices):
        LAB_REPORT = "LAB_REPORT", "Laboratory Report"
        PRESCRIPTION = "PRESCRIPTION", "Prescription Document"
        CONSULTATION = "CONSULTATION", "Consultation Note"
        DISCHARGE_SUMMARY = "DISCHARGE_SUMMARY", "Discharge Summary"
        IMAGING_REPORT = "IMAGING_REPORT", "Imaging Report"
        OTHER = "OTHER", "Other Medical Document"

    class ProcessingStatus(models.TextChoices):
        PENDING = "pending", "Pending Processing"
        PROCESSING = "processing", "Processing OCR / Vision"
        PROCESSED = "processed", "Processed & Indexed"
        FAILED = "failed", "Processing Failed"

    class ExtractionStatus(models.TextChoices):
        NOT_APPLICABLE = "not_applicable", "Not Applicable"
        DRAFT = "draft", "Draft Candidate Extraction"
        REVIEW_REQUIRED = "review_required", "Doctor Review Required"
        COMPLETED = "completed", "Extraction Completed"
        VERIFIED = "verified", "Doctor Verified & Approved"
        REJECTED = "rejected", "Rejected by Doctor"


    patient = models.ForeignKey(
        "patients.Patient",
        on_delete=models.CASCADE,
        related_name="medical_documents",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="uploaded_documents",
    )
    document_type = models.CharField(
        max_length=30,
        choices=DocumentType.choices,
        default=DocumentType.OTHER,
    )
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to=document_file_path)
    file_type = models.CharField(max_length=100, blank=True)
    file_size = models.IntegerField(default=0, help_text="File size in bytes")

    processing_status = models.CharField(
        max_length=20,
        choices=ProcessingStatus.choices,
        default=ProcessingStatus.PENDING,
    )
    extraction_status = models.CharField(
        max_length=20,
        choices=ExtractionStatus.choices,
        default=ExtractionStatus.NOT_APPLICABLE,
    )
    extracted_text = models.TextField(blank=True)
    extracted_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured clinical extraction findings, confidence scores, and provenance metadata.",
    )

    verified_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="verified_medical_documents",
        limit_choices_to={"role": "doctor"},
    )
    verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["patient", "document_type"]),
            models.Index(fields=["patient", "processing_status"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.get_document_type_display()}) - Patient #{self.patient_id}"
