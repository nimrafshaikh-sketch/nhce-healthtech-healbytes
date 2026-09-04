import logging
import os
import mimetypes
from django.db import transaction
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsDoctor, IsPatient
from apps.documents.embeddings import index_document_chunks, retrieve_patient_context_semantic
from apps.documents.models import MedicalDocument
from apps.documents.ocr import extract_text_from_file, extract_document_entities, sanitize_document_text
from apps.documents.serializers import (
    MedicalDocumentSerializer,
    MedicalDocumentUploadSerializer,
    PrescriptionVerificationSerializer,
)
from apps.medications.models import Medication
from apps.medications.serializers import MedicationSerializer
from apps.patients.models import Patient
from apps.qr.models import QRAccessGrant

logger = logging.getLogger(__name__)


class DocumentListCreateView(generics.ListCreateAPIView):
    """List documents for authorized patient or upload a new medical document."""
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        return MedicalDocumentUploadSerializer if self.request.method == "POST" else MedicalDocumentSerializer

    def get_queryset(self):
        user = self.request.user
        patient_id = self.request.query_params.get("patient")

        if getattr(user, "is_doctor", False):
            qs = MedicalDocument.objects.filter(patient__doctor=user)
            if patient_id:
                qs = qs.filter(patient_id=patient_id)
            return qs
        elif getattr(user, "is_patient", False):
            return MedicalDocument.objects.filter(patient__user=user)
        # Non-clinical staff (receptionist, lab tech) have no broad document access
        return MedicalDocument.objects.none()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        doc = self.perform_create(serializer)
        out_serializer = MedicalDocumentSerializer(doc)
        headers = self.get_success_headers(out_serializer.data)
        return Response(out_serializer.data, status=status.HTTP_201_CREATED, headers=headers)

    def perform_create(self, serializer):
        user = self.request.user
        validated_data = serializer.validated_data
        uploaded_file = validated_data["file"]

        # Resolve patient
        if getattr(user, "is_patient", False):
            patient = user.patient_profile
        else:
            patient = validated_data.get("patient")
            if not patient:
                raise ValidationError({"patient": "Doctor must specify target patient."})
            if getattr(user, "is_doctor", False) and patient.doctor_id != user.id:
                raise PermissionDenied("You can only upload documents for your own assigned patients.")

        # Determine MIME type & size
        file_type = uploaded_file.content_type or mimetypes.guess_type(uploaded_file.name)[0] or "application/octet-stream"
        file_size = uploaded_file.size

        doc = serializer.save(
            patient=patient,
            uploaded_by=user,
            file_type=file_type,
            file_size=file_size,
            processing_status=MedicalDocument.ProcessingStatus.PROCESSING,
        )

        # Run OCR extraction
        try:
            raw_text = extract_text_from_file(doc.file, file_type=file_type)
            # Sanitize BEFORE persisting: extracted_text is what RAG chunks
            # (apps.documents.rag.retrieve_patient_context) and any future
            # LLM would read. Previously only an ephemeral local copy inside
            # extract_document_entities() was sanitized while the raw,
            # unsanitized OCR/text-extraction output was stored and served
            # to retrieval - closing that gap here, not just at read time.
            sanitized_text = sanitize_document_text(raw_text)
            extraction_result = extract_document_entities(sanitized_text, doc.document_type)

            doc.extracted_text = sanitized_text
            doc.extracted_data = extraction_result
            doc.processing_status = MedicalDocument.ProcessingStatus.PROCESSED
            
            if doc.document_type == MedicalDocument.DocumentType.PRESCRIPTION:
                doc.extraction_status = MedicalDocument.ExtractionStatus.REVIEW_REQUIRED
            elif extraction_result.get("clinical_findings"):
                doc.extraction_status = MedicalDocument.ExtractionStatus.COMPLETED
            else:
                doc.extraction_status = MedicalDocument.ExtractionStatus.NOT_APPLICABLE
            doc.save()

            # Chunk + index for retrieval (Phase 1 pipeline's final step,
            # and the persisted store Phase 2 semantic retrieval reads
            # from). Failure here must never fail the upload itself - the
            # document and its OCR/extraction results are already saved and
            # correct; retrieval simply falls back to the existing
            # keyword/TF-cosine path (rag.py) for this document until
            # indexing succeeds.
            try:
                index_document_chunks(doc)
            except Exception:
                logger.exception("Chunk indexing failed for document %s; retrieval falls back to keyword search.", doc.id)
        except Exception as exc:
            doc.processing_status = MedicalDocument.ProcessingStatus.FAILED
            doc.save()
        return doc



class DocumentDetailView(generics.RetrieveAPIView):
    """Retrieve metadata and structured extraction for a specific medical document."""
    serializer_class = MedicalDocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if getattr(user, "is_doctor", False):
            return MedicalDocument.objects.filter(patient__doctor=user)
        elif getattr(user, "is_patient", False):
            return MedicalDocument.objects.filter(patient__user=user)
        return MedicalDocument.objects.none()


class DocumentStreamView(APIView):
    """Stream authorized medical document file to doctor or patient.
    Enforces strict backend authorization:
    - Primary assigned doctor
    - Temporary QR-verified consulting doctor (audited via QRScanLog)
    - Patient self
    All other actors (unauthorized doctors, receptionists, lab techs, anonymous) are rejected with HTTP 403.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        try:
            document = MedicalDocument.objects.select_related("patient").get(pk=pk)
        except MedicalDocument.DoesNotExist:
            raise Http404("Document not found.")

        user = request.user
        patient = document.patient

        # 1. Patient self access
        is_self_patient = getattr(user, "is_patient", False) and patient.user_id == user.id
        # 2. Primary doctor access
        is_primary_doctor = getattr(user, "is_doctor", False) and patient.doctor_id == user.id
        # 3. QR-verified consulting doctor access - bounded by an active,
        #    non-expired QRAccessGrant (see apps.qr.views.QRVerifyView),
        #    never by the mere existence of a permanent QRScanLog audit row.
        is_qr_doctor = getattr(user, "is_doctor", False) and QRAccessGrant.has_active_grant(patient=patient, doctor=user)

        if not (is_self_patient or is_primary_doctor or is_qr_doctor):
            raise PermissionDenied("You do not have authorization to view this medical document.")

        if not document.file or not os.path.exists(document.file.path):
            raise Http404("Document file content unavailable.")

        content_type = document.file_type or "application/octet-stream"
        response = FileResponse(open(document.file.path, "rb"), content_type=content_type)
        filename = os.path.basename(document.file.name)
        response["Content-Disposition"] = f'inline; filename="{filename}"'
        return response


class PrescriptionVerifyView(APIView):
    """Doctor verifies and approves candidate prescription extracted from an uploaded document.
    Ensures human-in-the-loop clinical review and prevents duplicate medications.
    """
    permission_classes = [permissions.IsAuthenticated, IsDoctor]

    @transaction.atomic
    def post(self, request, pk):
        document = get_object_or_404(MedicalDocument, pk=pk, patient__doctor=request.user)
        if document.document_type != MedicalDocument.DocumentType.PRESCRIPTION:
            return Response({"detail": "This document is not a prescription document."}, status=status.HTTP_400_BAD_REQUEST)

        serializer = PrescriptionVerificationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        patient = document.patient
        start_date = data.get("start_date") or timezone.now().date()

        # Check for existing active prescription to prevent accidental duplicates
        existing_med = Medication.objects.filter(
            patient=patient,
            name__iexact=data["name"].strip(),
            is_active=True
        ).first()

        if existing_med:
            # Update existing rather than duplicating
            existing_med.dosage = data["dosage"]
            existing_med.frequency = data["frequency"]
            existing_med.instructions = data.get("instructions", "")
            existing_med.start_date = start_date
            existing_med.end_date = data.get("end_date")
            existing_med.reminder_times = data.get("reminder_times", [])
            if not existing_med.prescribed_by:
                existing_med.prescribed_by = request.user
            existing_med.save()
            medication = existing_med
        else:
            medication = Medication.objects.create(
                patient=patient,
                prescribed_by=request.user,
                name=data["name"].strip(),
                dosage=data["dosage"],
                frequency=data["frequency"],
                instructions=data.get("instructions", ""),
                start_date=start_date,
                end_date=data.get("end_date"),
                reminder_times=data.get("reminder_times", []),
                is_active=True,
            )

        # Mark document as verified
        document.extraction_status = MedicalDocument.ExtractionStatus.VERIFIED
        document.verified_by = request.user
        document.verified_at = timezone.now()
        document.save(update_fields=["extraction_status", "verified_by", "verified_at"])

        return Response({
            "detail": "Prescription verified and structured medication record created.",
            "document_status": document.extraction_status,
            "medication": MedicationSerializer(medication).data,
            "document": MedicalDocumentSerializer(document).data,
        }, status=status.HTTP_200_OK)


class DocumentRAGSearchView(APIView):
    """Search clinical documents for a specific patient using patient-scoped RAG retrieval.
    Enforces server-side patient isolation before similarity computation.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        from apps.documents.rag import get_patient_rag_engine

        patient_id = request.query_params.get("patient_id")
        query = request.query_params.get("query", "")
        try:
            top_k = int(request.query_params.get("top_k", 5))
        except (ValueError, TypeError):
            top_k = 5

        if not patient_id:
            return Response({"detail": "patient_id query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

        patient = get_object_or_404(Patient, pk=patient_id)
        user = request.user

        # Authorization checks
        if getattr(user, "is_doctor", False):
            if patient.doctor_id != user.id:
                # Fall back to an active, non-expired QRAccessGrant created
                # by a prior successful QR verification (apps.qr.views.
                # QRVerifyView). QRScanLog has no `doctor`/`status`/
                # `scanned_at` fields - querying those crashed this check
                # with an unhandled FieldError (HTTP 500) instead of
                # denying access; fixed by using the real grant model.
                has_qr_access = QRAccessGrant.has_active_grant(patient=patient, doctor=user)
                if not has_qr_access:
                    raise PermissionDenied("You are not authorized to query documents for this patient.")
        elif getattr(user, "is_patient", False):
            if user.patient_profile.id != patient.id:
                raise PermissionDenied("You cannot access clinical records of another patient.")
        else:
            raise PermissionDenied("Non-clinical staff cannot access RAG retrieval.")

        # Phase 2: real semantic (embedding) retrieval is primary; the
        # original keyword/TF-cosine engine (rag.py, untouched) is the
        # explicit fallback - used whenever semantic retrieval genuinely
        # cannot run (no scikit-learn, or this patient has no indexed
        # chunks yet), never silently swapped in without saying so.
        results = retrieve_patient_context_semantic(patient_id=patient.id, query=query, top_k=top_k)
        retrieval_method = "semantic_embedding_lsa"
        if results is None:
            rag_engine = get_patient_rag_engine()
            results = rag_engine.retrieve_patient_context(patient_id=patient.id, query=query, top_k=top_k)
            retrieval_method = "keyword_tf_cosine_fallback"
            for r in results:
                r.setdefault("retrieval_method", retrieval_method)

        return Response({
            "patient_id": patient.id,
            "query": query,
            "retrieval_method": retrieval_method,
            "results": results,
            "count": len(results)
        }, status=status.HTTP_200_OK)


