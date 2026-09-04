"""Phase 4 - Patient Timeline: deterministic chronological aggregation.

Verifies real events from real records appear in the timeline (no
fabricated entries), that it's sorted chronologically, that Patient.id
anchors every event, and that the endpoint is scoped exactly like its
sibling analytics endpoints (assigned doctor / patient self only).
"""
from datetime import date, timedelta

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment
from apps.checkins.models import DailyCheckin
from apps.core.test_utils import auth_headers, make_doctor, make_patient_user
from apps.labtests.models import LabTestRequest, LabTestResult
from apps.medications.models import Medication
from apps.patients.models import Patient
from apps.patients.timeline import build_patient_timeline

TODAY = date.today()


class PatientTimelineLogicTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient = Patient.objects.create(doctor=self.doctor, full_name="Timeline Patient")

    def test_empty_patient_has_empty_timeline(self):
        result = build_patient_timeline(self.patient)
        self.assertEqual(result["events"], [])
        self.assertEqual(result["event_count"], 0)

    def test_appointment_medication_lab_checkin_document_all_appear(self):
        Appointment.objects.create(
            patient=self.patient, doctor=self.doctor, created_by=self.doctor,
            scheduled_at=timezone.now(), reason="Routine follow-up",
        )
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Metformin",
            dosage="500mg", frequency="twice_daily", start_date=TODAY, is_active=True,
        )
        req = LabTestRequest.objects.create(patient=self.patient, requested_by=self.doctor, test_name="HBA1C")
        LabTestResult.objects.create(request=req, result_text="HbA1c 7.9%")
        DailyCheckin.objects.create(
            patient=self.patient, checkin_date=TODAY, symptoms=["fatigue"],
            ai_risk_level=DailyCheckin.RiskLevel.MEDIUM, ai_notes="Elevated fatigue reported",
            ai_recommended_action="Care-team review recommended.", ai_processed_at=timezone.now(),
        )

        result = build_patient_timeline(self.patient)
        event_types = {e["event_type"] for e in result["events"]}
        self.assertIn("APPOINTMENT", event_types)
        self.assertIn("PRESCRIPTION_STARTED", event_types)
        self.assertIn("LAB_REQUESTED", event_types)
        self.assertIn("LAB_RESULT", event_types)
        self.assertIn("CHECK_IN", event_types)
        self.assertIn("AI_RISK_EVALUATION", event_types)
        self.assertIn("AI_FOLLOWUP_RECOMMENDATION", event_types)

        for event in result["events"]:
            self.assertEqual(event["patient_id"], self.patient.id)

    def test_events_sorted_most_recent_first(self):
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="Old Med",
            dosage="10mg", frequency="once_daily", start_date=TODAY - timedelta(days=100), is_active=False,
            end_date=TODAY - timedelta(days=50),
        )
        Medication.objects.create(
            patient=self.patient, prescribed_by=self.doctor, name="New Med",
            dosage="10mg", frequency="once_daily", start_date=TODAY, is_active=True,
        )
        result = build_patient_timeline(self.patient)
        dates = [e["date"] for e in result["events"]]
        self.assertEqual(dates, sorted(dates, reverse=True))

    def test_pending_checkin_produces_no_ai_risk_event(self):
        """A check-in still awaiting AI analysis must not fabricate an AI
        evaluation event that never happened."""
        DailyCheckin.objects.create(patient=self.patient, checkin_date=TODAY)
        result = build_patient_timeline(self.patient)
        event_types = {e["event_type"] for e in result["events"]}
        self.assertIn("CHECK_IN", event_types)
        self.assertNotIn("AI_RISK_EVALUATION", event_types)
        self.assertNotIn("AI_FOLLOWUP_RECOMMENDATION", event_types)


class PatientTimelineEndpointTests(APITestCase):
    def setUp(self):
        self.doctor_a = make_doctor(email="tda@example.com", username="tda")
        self.doctor_b = make_doctor(email="tdb@example.com", username="tdb")
        self.patient_user = make_patient_user(email="tpu@example.com", username="tpu")
        self.patient = Patient.objects.create(doctor=self.doctor_a, full_name="Timeline Endpoint Patient", user=self.patient_user)

    def test_assigned_doctor_can_view_timeline(self):
        resp = self.client.get(
            reverse("analytics-patient-timeline", args=[self.patient.id]), **auth_headers(self.doctor_a)
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("events", resp.data)

    def test_unassigned_doctor_cannot_view_timeline(self):
        resp = self.client.get(
            reverse("analytics-patient-timeline", args=[self.patient.id]), **auth_headers(self.doctor_b)
        )
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_patient_can_view_own_timeline(self):
        resp = self.client.get(reverse("analytics-me-timeline"), **auth_headers(self.patient_user))
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
