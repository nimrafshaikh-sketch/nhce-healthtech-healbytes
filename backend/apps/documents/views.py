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
from apps.medications.models import Medication, Prescription
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
            if patient_id and str(patient_id).isdigit():
                qs = qs.filter(patient_id=int(patient_id))
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

            findings = extraction_result.get("clinical_findings", [])
            candidate_meds = [f for f in findings if f.get("entity_type") == "CANDIDATE_PRESCRIPTION"]

            # Automatically populate active medication and prescription records for the patient
            if getattr(user, "is_doctor", False) and (doc.document_type == MedicalDocument.DocumentType.PRESCRIPTION or candidate_meds):
                for candidate in candidate_meds:
                    drug_name = candidate.get("drug_name") or candidate.get("name")
                    dosage = candidate.get("dosage") or "500mg"
                    frequency = candidate.get("frequency") or "once_daily"
                    instructions = candidate.get("instructions") or "Take as directed"

                    if frequency == "once_daily":
                        reminder_times = ["08:00"]
                    elif frequency == "twice_daily":
                        reminder_times = ["08:00", "20:00"]
                    elif frequency == "three_times_daily":
                        reminder_times = ["08:00", "13:00", "20:00"]
                    elif frequency == "weekly":
                        reminder_times = ["08:00"]
                    else:
                        reminder_times = ["08:00"]

                    if drug_name:
                        start_date = timezone.now().date()
                        duration_days = candidate.get("duration_days") or 10
                        end_date = start_date + timezone.timedelta(days=duration_days)
                        duration_str = candidate.get("duration") or f"{duration_days} days"

                        existing_med = Medication.objects.filter(
                            patient=patient,
                            name__iexact=drug_name.strip(),
                            is_active=True
                        ).first()

                        if existing_med:
                            existing_med.dosage = dosage
                            existing_med.frequency = frequency
                            existing_med.instructions = instructions
                            existing_med.reminder_times = reminder_times
                            existing_med.start_date = start_date
                            existing_med.end_date = end_date
                            existing_med.is_active = True
                            if not existing_med.prescribed_by:
                                existing_med.prescribed_by = user
                            existing_med.save()
                            med_obj = existing_med
                        else:
                            med_obj = Medication.objects.create(
                                patient=patient,
                                prescribed_by=user,
                                name=drug_name.strip(),
                                dosage=dosage,
                                frequency=frequency,
                                instructions=instructions,
                                start_date=start_date,
                                end_date=end_date,
                                reminder_times=reminder_times,
                                is_active=True,
                            )

                        Prescription.objects.create(
                            patient=patient,
                            doctor=user,
                            medication_name=drug_name.strip(),
                            dosage=dosage,
                            frequency=frequency,
                            duration=duration_str,
                            instructions=instructions,
                        )

                        if patient.user:
                            from apps.notifications.services import create_notification
                            schedule_str = ", ".join(reminder_times)
                            freq_label = frequency.replace("_", " ").title()
                            create_notification(
                                user=patient.user,
                                notification_type="medication_reminder",
                                title=f"New Prescription: {drug_name.strip()} ({dosage})",
                                body=f"Dr. {user.get_full_name() or user.last_name} prescribed {drug_name.strip()} ({dosage}), {freq_label}. Scheduled at: {schedule_str}. Instructions: {instructions}",
                                related_object_type="medication",
                                related_object_id=med_obj.id,
                            )

            if doc.document_type == MedicalDocument.DocumentType.PRESCRIPTION:
                doc.extraction_status = MedicalDocument.ExtractionStatus.COMPLETED if candidate_meds else MedicalDocument.ExtractionStatus.REVIEW_REQUIRED
                if candidate_meds:
                    doc.verified_by = user if getattr(user, "is_doctor", False) else None
                    doc.verified_at = timezone.now() if getattr(user, "is_doctor", False) else None
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
    Supports JWT Authorization header and `?token=<JWT>` query parameter for direct browser tab opens.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        user = request.user
        if not user or not user.is_authenticated:
            token = request.query_params.get("token")
            if token:
                try:
                    from rest_framework_simplejwt.tokens import AccessToken
                    from apps.accounts.models import User
                    validated_token = AccessToken(token)
                    user_id = validated_token.get("user_id")
                    user = User.objects.filter(id=user_id).first()
                except Exception:
                    user = None

        if not user or not user.is_authenticated:
            raise PermissionDenied("Authentication required to view this medical document.")

        try:
            document = MedicalDocument.objects.select_related("patient", "patient__doctor", "uploaded_by", "verified_by").get(pk=pk)
        except MedicalDocument.DoesNotExist:
            raise Http404("Document not found.")

        patient = document.patient

        # 1. Patient self access
        is_self_patient = getattr(user, "is_patient", False) and patient.user_id == user.id
        # 2. Primary doctor access
        is_primary_doctor = getattr(user, "is_doctor", False) and patient.doctor_id == user.id
        # 3. QR-verified consulting doctor access - bounded by an active,
        #    non-expired QRAccessGrant (see apps.qr.views.QRVerifyView)
        is_qr_doctor = getattr(user, "is_doctor", False) and QRAccessGrant.has_active_grant(patient=patient, doctor=user)

        if not (is_self_patient or is_primary_doctor or is_qr_doctor):
            raise PermissionDenied("You do not have authorization to view this medical document.")

        # If physical file exists on disk, stream it
        if document.file and hasattr(document.file, "path") and os.path.exists(document.file.path):
            content_type = document.file_type or mimetypes.guess_type(document.file.name)[0] or "application/octet-stream"
            response = FileResponse(open(document.file.path, "rb"), content_type=content_type)
            filename = os.path.basename(document.file.name)
            response["Content-Disposition"] = f'inline; filename="{filename}"'
            return response

        # Graceful fallback: render a structured, authenticated clinical document report
        import html
        from django.http import HttpResponse

        findings = (document.extracted_data or {}).get("clinical_findings", [])
        findings_html = ""
        if findings:
            findings_rows = []
            for f in findings:
                if not isinstance(f, dict):
                    continue
                etype = html.escape(str(f.get("entity_type", "FINDING")))
                name = html.escape(str(f.get("biomarker_name") or f.get("drug_name") or f.get("test_name") or f.get("name") or etype))
                val = html.escape(str(f.get("value") or f.get("dosage") or f.get("text") or "Present"))
                unit = html.escape(str(f.get("unit") or ""))
                status_badge = html.escape(str(f.get("status") or "RECORDED"))
                findings_rows.append(f"""
                <tr>
                    <td style="padding: 10px 14px; border-bottom: 1px solid #e2e8f0; font-weight: 600; color: #1e293b;">{name}</td>
                    <td style="padding: 10px 14px; border-bottom: 1px solid #e2e8f0; color: #334155;">{val} {unit}</td>
                    <td style="padding: 10px 14px; border-bottom: 1px solid #e2e8f0;"><span style="display:inline-block; padding: 2px 8px; font-size: 11px; font-weight: 600; border-radius: 9999px; background: #ecfdf5; color: #065f46;">{status_badge}</span></td>
                </tr>
                """)
            findings_html = f"""
            <div style="margin-top: 24px;">
                <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #475569; margin-bottom: 12px;">Structured Clinical Findings & Biomarkers</h3>
                <table style="width: 100%; border-collapse: collapse; background: #f8fafc; border-radius: 8px; overflow: hidden; border: 1px solid #e2e8f0; font-size: 13px;">
                    <thead>
                        <tr style="background: #e2e8f0; text-align: left; color: #475569; font-size: 11px; text-transform: uppercase; letter-spacing: 0.05em;">
                            <th style="padding: 10px 14px;">Entity / Test</th>
                            <th style="padding: 10px 14px;">Value / Measurement</th>
                            <th style="padding: 10px 14px;">Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {''.join(findings_rows)}
                    </tbody>
                </table>
            </div>
            """

        extracted_text_content = html.escape(document.extracted_text or "No extracted clinical text available.")
        created_date = document.created_at.strftime("%B %d, %Y at %I:%M %p") if document.created_at else "N/A"
        doc_title = html.escape(document.title or "Medical Document")
        doc_type = html.escape(document.get_document_type_display())
        patient_name = html.escape(patient.full_name)
        doctor_name = html.escape(patient.doctor.get_full_name() if patient.doctor else "Assigned Physician")

        html_doc = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{doc_title} - HealBytes Medical Document</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            color: #1e293b;
            padding: 32px 16px;
            display: flex;
            justify-content: center;
        }}
        .report-card {{
            background: #ffffff;
            width: 100%;
            max-width: 820px;
            border-radius: 16px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.2), 0 10px 10px -5px rgba(0, 0, 0, 0.1);
            overflow: hidden;
            border: 1px solid #e2e8f0;
        }}
        .report-header {{
            background: linear-gradient(135deg, #0d9488 0%, #0f766e 100%);
            color: white;
            padding: 24px 32px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .badge {{
            display: inline-block;
            background: rgba(255, 255, 255, 0.2);
            color: white;
            padding: 4px 12px;
            border-radius: 9999px;
            font-size: 12px;
            font-weight: 600;
            letter-spacing: 0.05em;
            text-transform: uppercase;
        }}
        .report-body {{
            padding: 32px;
        }}
        .meta-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 12px;
            padding: 16px 20px;
            margin-bottom: 24px;
        }}
        .meta-item label {{
            display: block;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: #64748b;
            font-weight: 600;
            margin-bottom: 4px;
        }}
        .meta-item span {{
            display: block;
            font-size: 14px;
            color: #0f172a;
            font-weight: 600;
        }}
        .text-section {{
            margin-top: 24px;
        }}
        .text-box {{
            background: #f8fafc;
            border: 1px solid #cbd5e1;
            border-radius: 10px;
            padding: 18px 20px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
            font-size: 13px;
            line-height: 1.6;
            color: #334155;
            white-space: pre-wrap;
            word-break: break-word;
            max-height: 480px;
            overflow-y: auto;
        }}
        .actions {{
            display: flex;
            gap: 12px;
            justify-content: flex-end;
            padding: 20px 32px;
            background: #f8fafc;
            border-top: 1px solid #e2e8f0;
        }}
        .btn {{
            padding: 8px 18px;
            border-radius: 8px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            border: 1px solid transparent;
            text-decoration: none;
            display: inline-flex;
            align-items: center;
        }}
        .btn-primary {{
            background: #0d9488;
            color: white;
        }}
        .btn-secondary {{
            background: #ffffff;
            color: #475569;
            border-color: #cbd5e1;
        }}
        @media print {{
            body {{ background: white; padding: 0; }}
            .actions {{ display: none; }}
            .report-card {{ box-shadow: none; border: none; max-width: 100%; }}
        }}
    </style>
</head>
<body>
    <div class="report-card">
        <div class="report-header">
            <div>
                <h1 style="font-size: 20px; font-weight: 800; margin-bottom: 4px; letter-spacing: -0.02em;">HealBytes Clinical Intelligence</h1>
                <p style="font-size: 13px; opacity: 0.9;">Authoritative Patient Document Record</p>
            </div>
            <span class="badge">{doc_type}</span>
        </div>
        <div class="report-body">
            <h2 style="font-size: 18px; font-weight: 700; color: #0f172a; margin-bottom: 16px;">{doc_title}</h2>
            
            <div class="meta-grid">
                <div class="meta-item">
                    <label>Patient Name</label>
                    <span>{patient_name}</span>
                </div>
                <div class="meta-item">
                    <label>Primary Physician</label>
                    <span>{doctor_name}</span>
                </div>
                <div class="meta-item">
                    <label>Document Date</label>
                    <span>{created_date}</span>
                </div>
                <div class="meta-item">
                    <label>Verification Status</label>
                    <span>{html.escape(document.extraction_status or document.processing_status)}</span>
                </div>
            </div>

            {findings_html}

            <div class="text-section">
                <h3 style="font-size: 13px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; color: #475569; margin-bottom: 10px;">Document Content & Extracted Text</h3>
                <div class="text-box">{extracted_text_content}</div>
            </div>
        </div>
        <div class="actions">
            <button onclick="window.print()" class="btn btn-primary">Print Report</button>
            <button onclick="window.close()" class="btn btn-secondary">Close Window</button>
        </div>
    </div>
</body>
</html>"""
        return HttpResponse(html_doc, content_type="text/html")


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
        frequency = data["frequency"]

        # Determine standard reminder times if not provided
        reminder_times = data.get("reminder_times")
        if not reminder_times:
            if frequency == "once_daily":
                reminder_times = ["08:00"]
            elif frequency == "twice_daily":
                reminder_times = ["08:00", "20:00"]
            elif frequency == "three_times_daily":
                reminder_times = ["08:00", "13:00", "20:00"]
            elif frequency == "weekly":
                reminder_times = ["08:00"]
            else:
                reminder_times = ["08:00"]

        # Check for existing active prescription to prevent accidental duplicates
        existing_med = Medication.objects.filter(
            patient=patient,
            name__iexact=data["name"].strip(),
            is_active=True
        ).first()

        if existing_med:
            # Update existing rather than duplicating
            existing_med.dosage = data["dosage"]
            existing_med.frequency = frequency
            existing_med.instructions = data.get("instructions", "")
            existing_med.start_date = start_date
            existing_med.end_date = data.get("end_date")
            existing_med.reminder_times = reminder_times
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
                frequency=frequency,
                instructions=data.get("instructions", ""),
                start_date=start_date,
                end_date=data.get("end_date"),
                reminder_times=reminder_times,
                is_active=True,
            )

        # Mark document as verified
        document.extraction_status = MedicalDocument.ExtractionStatus.VERIFIED
        document.verified_by = request.user
        document.verified_at = timezone.now()
        document.save(update_fields=["extraction_status", "verified_by", "verified_at"])

        # Also record corresponding Prescription entry
        Prescription.objects.create(
            patient=patient,
            doctor=request.user,
            medication_name=data["name"].strip(),
            dosage=data["dosage"],
            frequency=frequency,
            duration="Ongoing",
            instructions=data.get("instructions", ""),
        )

        # In-app notification to patient
        if patient.user:
            from apps.notifications.services import create_notification
            schedule_str = ", ".join(reminder_times)
            freq_label = frequency.replace("_", " ").title()
            create_notification(
                user=patient.user,
                notification_type="medication_reminder",
                title=f"Prescription Verified: {data['name'].strip()} ({data['dosage']})",
                body=f"Dr. {request.user.get_full_name() or request.user.last_name} verified your prescription for {data['name'].strip()} ({data['dosage']}), {freq_label}. Scheduled times: {schedule_str}. Instructions: {data.get('instructions', 'Take as directed')}",
                related_object_type="medication",
                related_object_id=medication.id,
            )

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


