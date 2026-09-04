"""Phase 7 - Clinical Safety / Grounding verification.

Verifies the deterministic grounding pass: it re-checks cited ids against
the real database (not just the brief's own claims), catches cross-patient
identity violations if they ever occurred, and removes/flags any AI
Observation string that isn't traceable to real underlying data. Since the
current pipeline is 100% deterministic (no LLM), a correctly-built brief
should always pass every check - these tests confirm that, and separately
prove the "unsupported claim" detector actually fires on a fabricated one.
"""
from datetime import date

from rest_framework.test import APITestCase

from apps.core.test_utils import make_doctor
from apps.medications.models import Medication
from apps.patients.clinical_brief import build_clinical_brief
from apps.patients.grounding import verify_clinical_brief_grounding
from apps.patients.models import Patient

TODAY = date.today()


class GroundingVerificationTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="Grounding Patient")

    def test_freshly_built_brief_passes_every_check(self):
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Metformin",
            dosage="500mg", frequency="twice_daily", start_date=TODAY, is_active=True,
        )
        result = build_clinical_brief(self.patient)
        grounding = result["clinical_brief"]["grounding"]
        self.assertTrue(grounding["all_checks_passed"], grounding["checks"])
        self.assertEqual(grounding["unsupported_claims_removed"], [])

    def test_fabricated_unattributed_observation_is_detected_and_removed(self):
        """Directly exercises the verifier (not through build_clinical_brief)
        with a brief that has a claim not backed by any real trend/record -
        proving the detector actually fires, not just always passing."""
        fake_brief = {
            "active_medications": [],
            "recent_labs": [],
            "rag_evidence_excerpts": [],
            "source_documents": [],
            "important_trends": [],
            "recent_clinical_events": [],
            "medication_intelligence": {"observations": []},
            "ai_observations": ["AI Observation: This condition is definitely terminal."],
        }
        report = verify_clinical_brief_grounding(self.patient, fake_brief)
        self.assertFalse(report["all_checks_passed"])
        self.assertIn("AI Observation: This condition is definitely terminal.", report["unsupported_claims_removed"])
        self.assertEqual(report["grounded_ai_observations"], [])

    def test_medication_from_another_patient_fails_identity_check(self):
        """Simulates the kind of bug this check exists to catch: a brief
        citing a medication id that belongs to a different patient."""
        other_patient = Patient.objects.create(doctor=self.doctor, full_name="Other Patient")
        other_med = Medication.objects.create(
            patient=other_patient, prescribed_by=self.doctor, name="Warfarin",
            dosage="5mg", frequency="once_daily", start_date=TODAY, is_active=True,
        )
        fake_brief = {
            "active_medications": [{"id": other_med.id, "name": "Warfarin", "dosage": "5mg"}],
            "recent_labs": [],
            "rag_evidence_excerpts": [],
            "source_documents": [],
            "important_trends": [],
            "recent_clinical_events": [],
            "medication_intelligence": {"observations": []},
            "ai_observations": [],
        }
        report = verify_clinical_brief_grounding(self.patient, fake_brief)
        self.assertFalse(report["all_checks_passed"])
        identity_check = next(c for c in report["checks"] if c["check"] == "patient_identity_medications")
        self.assertFalse(identity_check["passed"])

    def test_conflicts_are_surfaced_not_hidden(self):
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Lisinopril",
            dosage="10mg", frequency="once_daily", start_date=TODAY, is_active=True,
        )
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Lisinopril",
            dosage="20mg", frequency="once_daily", start_date=TODAY, is_active=True,
        )
        result = build_clinical_brief(self.patient)
        grounding = result["clinical_brief"]["grounding"]
        self.assertGreaterEqual(len(grounding["conflicts"]), 1)
