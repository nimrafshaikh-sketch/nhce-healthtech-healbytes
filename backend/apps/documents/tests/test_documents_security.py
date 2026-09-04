"""Adversarial security tests for the MedicalDocument / RAG endpoints.

These exist specifically to close the gaps an independent security audit
found in the uncommitted "Phase 2" work: a deleted QR authorization check
(any doctor could access any patient's full record via QR), and a broken
RAG authorization fallback that crashed with an unhandled FieldError
(HTTP 500) instead of denying access with 403. Every test here asserts the
*security-relevant* outcome (who is let in, who is kept out, and how) - not
just "the endpoint returns 200 for the happy path."
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor, make_lab_tech, make_patient_user, make_receptionist
from apps.documents.models import MedicalDocument
from apps.patients.models import Patient
from apps.qr.models import QRAccessGrant


def _txt(name, content):
    return SimpleUploadedFile(name, content.encode("utf-8"), content_type="text/plain")


class DocumentAccessSecurityTests(APITestCase):
    """IDOR / role-boundary tests on document list, detail, and stream."""

    def setUp(self):
        self.doctor_a = make_doctor(email="doctor.a@example.com", username="doctora")
        self.doctor_b = make_doctor(email="doctor.b@example.com", username="doctorb")
        self.receptionist = make_receptionist()
        self.lab_tech = make_lab_tech()

        self.patient_a_user = make_patient_user(email="pa@example.com", username="pa")
        self.patient_b_user = make_patient_user(email="pb@example.com", username="pb")
        self.patient_a = Patient.objects.create(doctor=self.doctor_a, full_name="Patient A", user=self.patient_a_user)
        self.patient_b = Patient.objects.create(doctor=self.doctor_a, full_name="Patient B", user=self.patient_b_user)

        self.doc_a = MedicalDocument.objects.create(
            patient=self.patient_a, uploaded_by=self.doctor_a, document_type=MedicalDocument.DocumentType.LAB_REPORT,
            title="Patient A Lab", file=_txt("a.txt", "HbA1c: 7.9%"),
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
            extracted_text="HbA1c: 7.9%",
        )
        self.doc_b = MedicalDocument.objects.create(
            patient=self.patient_b, uploaded_by=self.doctor_a, document_type=MedicalDocument.DocumentType.LAB_REPORT,
            title="Patient B Confidential Lab", file=_txt("b.txt", "Creatinine: 2.8 mg/dL - Severe Renal Risk"),
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
            extracted_text="Creatinine: 2.8 mg/dL - Severe Renal Risk",
        )

    def _stream_url(self, doc):
        return reverse("document-view", args=[doc.id])

    # --- Assigned doctor: always authorized -----------------------------

    def test_assigned_doctor_can_stream_own_patients_document(self):
        resp = self.client.get(self._stream_url(self.doc_a), **auth_headers(self.doctor_a))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # --- Unassigned doctor without a grant: denied -----------------------

    def test_unassigned_doctor_without_grant_is_denied(self):
        resp = self.client.get(self._stream_url(self.doc_a), **auth_headers(self.doctor_b))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # --- Unassigned doctor WITH a valid grant: authorized, but only for
    #     the patient the grant names ------------------------------------

    def test_unassigned_doctor_with_active_grant_can_stream_that_patients_document(self):
        QRAccessGrant.grant(patient=self.patient_a, doctor=self.doctor_b)
        resp = self.client.get(self._stream_url(self.doc_a), **auth_headers(self.doctor_b))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_grant_for_patient_a_does_not_authorize_patient_b_document(self):
        QRAccessGrant.grant(patient=self.patient_a, doctor=self.doctor_b)
        resp = self.client.get(self._stream_url(self.doc_b), **auth_headers(self.doctor_b))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_expired_grant_no_longer_authorizes_streaming(self):
        QRAccessGrant.objects.create(
            patient=self.patient_a, doctor=self.doctor_b,
            expires_at=timezone.now() - timezone.timedelta(minutes=1),
        )
        resp = self.client.get(self._stream_url(self.doc_a), **auth_headers(self.doctor_b))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # --- Non-clinical roles: always denied, regardless of any grant ------

    def test_receptionist_cannot_stream_clinical_document(self):
        resp = self.client.get(self._stream_url(self.doc_a), **auth_headers(self.receptionist))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_lab_tech_cannot_stream_clinical_document(self):
        resp = self.client.get(self._stream_url(self.doc_a), **auth_headers(self.lab_tech))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unauthenticated_request_is_rejected(self):
        resp = self.client.get(self._stream_url(self.doc_a))
        self.assertIn(resp.status_code, (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))

    # --- Patient-to-patient IDOR -----------------------------------------

    def test_patient_cannot_stream_another_patients_document(self):
        resp = self.client.get(self._stream_url(self.doc_b), **auth_headers(self.patient_a_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_can_stream_own_document(self):
        resp = self.client.get(self._stream_url(self.doc_a), **auth_headers(self.patient_a_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # --- Document list is queryset-scoped, not just detail-guarded -------

    def test_lab_tech_document_list_is_empty_not_403_leak(self):
        resp = self.client.get(reverse("document-list-create"), **auth_headers(self.lab_tech))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        results = resp.data.get("results", resp.data)
        self.assertEqual(len(results), 0)


class DocumentRAGSecuritytests(APITestCase):
    """RAG-specific: patient isolation, and the authorization-fallback bug
    (unauthorized requests must get 403, never an unhandled 500)."""

    def setUp(self):
        self.doctor_a = make_doctor(email="doctor.a@example.com", username="doctora")
        self.doctor_b = make_doctor(email="doctor.b@example.com", username="doctorb")
        self.receptionist = make_receptionist()

        self.patient_a = Patient.objects.create(doctor=self.doctor_a, full_name="Patient A")
        self.patient_b = Patient.objects.create(doctor=self.doctor_a, full_name="Patient B")

        MedicalDocument.objects.create(
            patient=self.patient_a, uploaded_by=self.doctor_a, document_type=MedicalDocument.DocumentType.LAB_REPORT,
            title="A Lab", file=_txt("a.txt", "Patient A HbA1c 7.9 elevated"),
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
            extracted_text="Patient A HbA1c 7.9 elevated",
        )
        MedicalDocument.objects.create(
            patient=self.patient_b, uploaded_by=self.doctor_a, document_type=MedicalDocument.DocumentType.LAB_REPORT,
            title="B Confidential Lab", file=_txt("b.txt", "Patient B Creatinine 99.9 critical severe renal risk"),
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
            extracted_text="Patient B Creatinine 99.9 critical severe renal risk",
        )

    def _rag_url(self, patient_id, query):
        return f"{reverse('document-rag-search')}?patient_id={patient_id}&query={query}"

    def test_owning_doctor_rag_search_never_returns_other_patients_chunks(self):
        resp = self.client.get(
            self._rag_url(self.patient_a.id, "creatinine 99.9 critical severe renal risk"),
            **auth_headers(self.doctor_a),
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        for chunk in resp.data["results"]:
            self.assertEqual(chunk["patient_id"], self.patient_a.id)
            self.assertNotIn("99.9", chunk["chunk_text"])
            self.assertNotIn("Patient B", chunk["chunk_text"])

    def test_unauthorized_doctor_rag_search_is_403_not_500(self):
        """This is the exact regression an unhandled FieldError caused:
        querying QRScanLog.doctor/status/scanned_at (fields that don't
        exist) crashed with a 500 instead of denying access. Must be a
        clean 403 with zero results, not a server error."""
        resp = self.client.get(self._rag_url(self.patient_a.id, "hba1c"), **auth_headers(self.doctor_b))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_with_active_grant_can_rag_search(self):
        QRAccessGrant.grant(patient=self.patient_a, doctor=self.doctor_b)
        resp = self.client.get(self._rag_url(self.patient_a.id, "hba1c"), **auth_headers(self.doctor_b))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_expired_grant_rag_search_is_403(self):
        from django.utils import timezone as tz
        QRAccessGrant.objects.create(
            patient=self.patient_a, doctor=self.doctor_b,
            expires_at=tz.now() - tz.timedelta(hours=1),
        )
        resp = self.client.get(self._rag_url(self.patient_a.id, "hba1c"), **auth_headers(self.doctor_b))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_grant_for_patient_a_does_not_authorize_rag_on_patient_b(self):
        QRAccessGrant.grant(patient=self.patient_a, doctor=self.doctor_b)
        resp = self.client.get(self._rag_url(self.patient_b.id, "creatinine"), **auth_headers(self.doctor_b))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_receptionist_cannot_use_rag_search(self):
        resp = self.client.get(self._rag_url(self.patient_a.id, "hba1c"), **auth_headers(self.receptionist))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_cannot_rag_search_another_patients_scope(self):
        patient_a_user = make_patient_user(email="pa2@example.com", username="pa2")
        self.patient_a.user = patient_a_user
        self.patient_a.save(update_fields=["user"])
        resp = self.client.get(self._rag_url(self.patient_b.id, "creatinine"), **auth_headers(patient_a_user))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
