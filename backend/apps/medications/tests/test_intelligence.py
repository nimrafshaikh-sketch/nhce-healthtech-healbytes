"""Phase 3 - Medication Intelligence: deterministic reconciliation.

Verifies real reconciliation over real data (no mocked findings): duplicate
active medications, dosage-conflicting active medications, regimen changes
over time, document-vs-structured discrepancies, undocumented candidates,
and that nothing here ever writes to the Medication table. Also verifies
the endpoint's authorization mirrors the document RAG endpoint (assigned
doctor / active QR grant / patient self / everyone else denied).
"""
from datetime import timedelta
from django.utils import timezone

from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from apps.core.test_utils import auth_headers, make_doctor, make_patient_user, make_receptionist
from apps.documents.models import MedicalDocument
from apps.medications.intelligence import analyze_patient_medications
from apps.medications.models import Medication
from apps.patients.models import Patient
from apps.qr.models import QRAccessGrant

TODAY = timezone.localdate()


class MedicationIntelligenceLogicTests(APITestCase):
    """Direct unit tests against analyze_patient_medications() - no HTTP."""

    def setUp(self):
        self.doctor = make_doctor()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="Med Intel Patient")

    def test_never_writes_to_medication_table(self):
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Metformin",
            dosage="500mg", frequency="twice_daily", start_date=TODAY, is_active=True,
        )
        before = list(Medication.objects.filter(patient=self.patient).values())
        analyze_patient_medications(self.patient.id)
        after = list(Medication.objects.filter(patient=self.patient).values())
        self.assertEqual(before, after)

    def test_duplicate_active_medication_detected(self):
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Metformin",
            dosage="500mg", frequency="twice_daily", start_date=TODAY, is_active=True,
        )
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="metformin",  # same drug, different case
            dosage="500mg", frequency="twice_daily", start_date=TODAY, is_active=True,
        )
        result = analyze_patient_medications(self.patient.id)
        cats = [o["category"] for o in result["observations"]]
        self.assertIn("duplicate_active_medication", cats)

    def test_conflicting_dosage_active_medication_detected(self):
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Lisinopril",
            dosage="10mg", frequency="once_daily", start_date=TODAY, is_active=True,
        )
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Lisinopril",
            dosage="20mg", frequency="once_daily", start_date=TODAY, is_active=True,
        )
        result = analyze_patient_medications(self.patient.id)
        cats = [o["category"] for o in result["observations"]]
        self.assertIn("conflicting_active_medication", cats)

    def test_regimen_change_over_time_detected(self):
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Amlodipine",
            dosage="5mg", frequency="once_daily",
            start_date=TODAY - timedelta(days=200), end_date=TODAY - timedelta(days=30),
            is_active=False,
        )
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Amlodipine",
            dosage="10mg", frequency="once_daily", start_date=TODAY - timedelta(days=29), is_active=True,
        )
        result = analyze_patient_medications(self.patient.id)
        cats = [o["category"] for o in result["observations"]]
        self.assertIn("medication_regimen_changed_over_time", cats)
        self.assertEqual(len(result["current_medications"]), 1)
        self.assertEqual(len(result["historical_medications"]), 1)

    def test_document_structured_discrepancy_detected(self):
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Metformin",
            dosage="500mg", frequency="twice_daily", start_date=TODAY, is_active=True,
        )
        MedicalDocument.objects.create(
            patient=self.patient, uploaded_by=self.doctor,
            document_type=MedicalDocument.DocumentType.PRESCRIPTION,
            title="Discrepant prescription",
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
            extraction_status=MedicalDocument.ExtractionStatus.REVIEW_REQUIRED,
            extracted_data={
                "clinical_findings": [{
                    "entity_type": "CANDIDATE_PRESCRIPTION",
                    "drug_name": "Metformin",
                    "dosage": "1000mg",  # differs from the structured record
                    "frequency": "twice_daily",
                    "confidence": 0.9,
                    "is_verified": False,
                }],
            },
        )
        result = analyze_patient_medications(self.patient.id)
        cats = [o["category"] for o in result["observations"]]
        self.assertIn("document_structured_discrepancy", cats)

    def test_undocumented_candidate_medication_detected(self):
        MedicalDocument.objects.create(
            patient=self.patient, uploaded_by=self.doctor,
            document_type=MedicalDocument.DocumentType.PRESCRIPTION,
            title="New prescription, not yet verified",
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
            extraction_status=MedicalDocument.ExtractionStatus.REVIEW_REQUIRED,
            extracted_data={
                "clinical_findings": [{
                    "entity_type": "CANDIDATE_PRESCRIPTION",
                    "drug_name": "Atorvastatin",
                    "dosage": "20mg",
                    "frequency": "once_daily",
                    "confidence": 0.9,
                    "is_verified": False,
                }],
            },
        )
        result = analyze_patient_medications(self.patient.id)
        cats = [o["category"] for o in result["observations"]]
        self.assertIn("undocumented_candidate_medication", cats)
        self.assertEqual(len(result["unverified_document_candidates"]), 1)

    def test_verified_candidate_produces_no_undocumented_observation(self):
        """Once a doctor has verified a candidate (extraction_status ==
        VERIFIED), it should no longer be flagged as an outstanding gap."""
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Atorvastatin",
            dosage="20mg", frequency="once_daily", start_date=TODAY, is_active=True,
        )
        MedicalDocument.objects.create(
            patient=self.patient, uploaded_by=self.doctor,
            document_type=MedicalDocument.DocumentType.PRESCRIPTION,
            title="Verified prescription",
            processing_status=MedicalDocument.ProcessingStatus.PROCESSED,
            extraction_status=MedicalDocument.ExtractionStatus.VERIFIED,
            verified_by=self.doctor,
            extracted_data={
                "clinical_findings": [{
                    "entity_type": "CANDIDATE_PRESCRIPTION",
                    "drug_name": "Atorvastatin",
                    "dosage": "20mg",
                    "frequency": "once_daily",
                    "confidence": 0.9,
                    "is_verified": True,
                }],
            },
        )
        result = analyze_patient_medications(self.patient.id)
        cats = [o["category"] for o in result["observations"]]
        self.assertNotIn("undocumented_candidate_medication", cats)
        self.assertEqual(len(result["unverified_document_candidates"]), 0)

    def test_no_medications_no_documents_produces_empty_clean_result(self):
        result = analyze_patient_medications(self.patient.id)
        self.assertEqual(result["observations"], [])
        self.assertEqual(result["current_medications"], [])
        self.assertEqual(result["historical_medications"], [])


class MedicationIntelligenceEndpointTests(APITestCase):
    def setUp(self):
        self.doctor_a = make_doctor(email="doca@example.com", username="doca")
        self.doctor_b = make_doctor(email="docb@example.com", username="docb")
        self.receptionist = make_receptionist()
        self.patient_user = make_patient_user()
        self.patient = Patient.objects.create(doctor=self.doctor_a, full_name="Endpoint Patient", user=self.patient_user)
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor_a, name="Losartan",
            dosage="50mg", frequency="once_daily", start_date=TODAY, is_active=True,
        )

    def _url(self):
        return f"{reverse('medication-intelligence')}?patient_id={self.patient.id}"

    def test_assigned_doctor_can_view(self):
        resp = self.client.get(self._url(), **auth_headers(self.doctor_a))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["current_medications"]), 1)

    def test_patient_can_view_own_intelligence(self):
        resp = self.client.get(self._url(), **auth_headers(self.patient_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_unassigned_doctor_without_grant_is_denied(self):
        resp = self.client.get(self._url(), **auth_headers(self.doctor_b))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_unassigned_doctor_with_active_grant_is_allowed(self):
        QRAccessGrant.grant(patient=self.patient, doctor=self.doctor_b)
        resp = self.client.get(self._url(), **auth_headers(self.doctor_b))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_receptionist_is_denied(self):
        resp = self.client.get(self._url(), **auth_headers(self.receptionist))
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_missing_patient_id_is_400(self):
        resp = self.client.get(reverse("medication-intelligence"), **auth_headers(self.doctor_a))
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
