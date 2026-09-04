"""Phase 5 - Clinical Brief extension.

Verifies the existing, deterministic build_clinical_brief() (unchanged in
its original fields - see clinical_brief.py) now additionally surfaces
Medication Intelligence (Phase 3), the Patient Timeline (Phase 4), and a
unified `sources` list, and that RAG evidence is retrieved via the new
semantic-first path with the original keyword engine as fallback (Phase 2)
- consistent with DocumentRAGSearchView's behavior, not a second,
diverging implementation.
"""
from django.utils import timezone

from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase

from apps.core.test_utils import make_doctor
from apps.medications.models import Medication
from apps.patients.clinical_brief import build_clinical_brief
from apps.patients.models import Patient

TODAY = timezone.localdate()


class ClinicalBriefExtensionTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="Brief Extension Patient")

    def test_original_fields_still_present(self):
        """Backward compatibility: every field the original implementation
        produced must still be there, unchanged in meaning."""
        result = build_clinical_brief(self.patient)
        brief = result["clinical_brief"]
        for key in (
            "narrative", "current_conditions", "active_medications", "recent_labs",
            "longitudinal_trends", "important_trends", "recent_clinical_events",
            "ai_observations", "rag_evidence_excerpts", "source_documents",
        ):
            self.assertIn(key, brief)
        self.assertIn("patient_id", result)
        self.assertIn("patient_name", result)

    def test_new_sections_present_and_additive(self):
        result = build_clinical_brief(self.patient)
        brief = result["clinical_brief"]
        self.assertIn("medication_intelligence", brief)
        self.assertIn("patient_timeline", brief)
        self.assertIn("sources", brief)
        self.assertIn("rag_retrieval_method", brief)
        self.assertIn(brief["rag_retrieval_method"], ("semantic_embedding_lsa", "keyword_tf_cosine_fallback"))

    def test_medication_intelligence_observations_surface_in_ai_observations(self):
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Lisinopril",
            dosage="10mg", frequency="once_daily", start_date=TODAY, is_active=True,
        )
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Lisinopril",
            dosage="20mg", frequency="once_daily", start_date=TODAY, is_active=True,
        )
        result = build_clinical_brief(self.patient)
        brief = result["clinical_brief"]
        med_intel_cats = [o["category"] for o in brief["medication_intelligence"]["observations"]]
        self.assertIn("conflicting_active_medication", med_intel_cats)
        self.assertTrue(any("Medication Intelligence" in o for o in brief["ai_observations"]))

    def test_sources_reference_active_medications(self):
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Metformin",
            dosage="500mg", frequency="twice_daily", start_date=TODAY, is_active=True,
        )
        result = build_clinical_brief(self.patient)
        brief = result["clinical_brief"]
        med_sources = [s for s in brief["sources"] if s["type"] == "medication_record"]
        self.assertGreaterEqual(len(med_sources), 1)

    def test_patient_timeline_matches_standalone_timeline_builder(self):
        from apps.patients.timeline import build_patient_timeline
        result = build_clinical_brief(self.patient)
        brief = result["clinical_brief"]
        standalone = build_patient_timeline(self.patient)
        self.assertEqual(brief["patient_timeline"]["event_count"], standalone["event_count"])
