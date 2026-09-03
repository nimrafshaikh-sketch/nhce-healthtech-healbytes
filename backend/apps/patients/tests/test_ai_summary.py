from datetime import date, timedelta
from unittest.mock import patch

from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.appointments.models import Appointment
from apps.checkins.ai_client import _serialize_patient_history_request
from apps.checkins.models import DailyCheckin
from apps.core.test_utils import auth_headers, make_doctor, make_patient_user
from apps.labtests.models import LabTestRequest, LabTestResult
from apps.medications.models import Medication, MedicationReminderLog
from apps.patients.models import Patient


class AISummaryEndpointTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor(email="doc1@example.com", username="doc1")
        self.other_doctor = make_doctor(email="doc2@example.com", username="doc2")
        self.patient_user = make_patient_user(email="pat1@example.com", username="pat1")

        self.patient = Patient.objects.create(
            doctor=self.doctor,
            user=self.patient_user,
            full_name="Alice Smith",
            medical_notes="Hypertension\nAllergic to Penicillin",
        )
        self.other_patient = Patient.objects.create(
            doctor=self.other_doctor,
            full_name="Bob Jones",
        )

        self.doc_headers = auth_headers(self.doctor)
        self.pat_headers = auth_headers(self.patient_user)

    @patch("apps.patients.analytics_views.get_patient_history_summary")
    def test_doctor_can_get_ai_summary_for_assigned_patient(self, mock_summary):
        mock_summary.return_value = {
            "request_id": "summary_1_123",
            "timestamp": timezone.now().isoformat(),
            "history": {
                "checkin_count": 2,
                "days_since_last_checkin": 0,
                "symptom_trend": {"trend": "stable", "detail": "stable"},
                "vital_trend": {},
                "medications": [],
                "latest_lab": None,
                "open_follow_up": None,
                "medication_adherence": {"overall_status": "unknown", "medications": []},
            },
        }

        url = reverse("analytics-patient-ai-summary", args=[self.patient.id])
        resp = self.client.get(url, **self.doc_headers)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["request_id"], "summary_1_123")
        self.assertEqual(resp.data["history"]["checkin_count"], 2)
        mock_summary.assert_called_once_with(self.patient)

    def test_doctor_cannot_get_ai_summary_for_unassigned_patient(self):
        url = reverse("analytics-patient-ai-summary", args=[self.other_patient.id])
        resp = self.client.get(url, **self.doc_headers)
        self.assertEqual(resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_unauthenticated_request_rejected(self):
        url = reverse("analytics-patient-ai-summary", args=[self.patient.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_patient_cannot_access_doctor_ai_summary_endpoint(self):
        url = reverse("analytics-patient-ai-summary", args=[self.patient.id])
        resp = self.client.get(url, **self.pat_headers)
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    @patch("apps.patients.analytics_views.get_patient_history_summary")
    def test_patient_can_get_own_ai_summary_via_me(self, mock_summary):
        mock_summary.return_value = {
            "request_id": "summary_me_123",
            "history": {"checkin_count": 1},
        }
        url = reverse("analytics-me-ai-summary")
        resp = self.client.get(url, **self.pat_headers)

        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["request_id"], "summary_me_123")
        mock_summary.assert_called_once_with(self.patient)

    @patch("apps.patients.analytics_views.get_patient_history_summary")
    def test_ai_engine_unavailable_returns_503(self, mock_summary):
        mock_summary.return_value = None
        url = reverse("analytics-patient-ai-summary", args=[self.patient.id])
        resp = self.client.get(url, **self.doc_headers)

        self.assertEqual(resp.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("detail", resp.data)


class AIPatientHistorySerializationTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient = Patient.objects.create(
            doctor=self.doctor,
            full_name="Test Patient",
            medical_notes="Type 2 Diabetes\nAsthma",
        )

    def test_serialization_with_all_history_records(self):
        # 1. Check-in
        c1 = DailyCheckin.objects.create(
            patient=self.patient,
            checkin_date=date.today() - timedelta(days=2),
            symptoms=["Cough", "Fatigue"],
            pain_level=2,
            vitals={"heart_rate": 72.0, "temperature_c": 36.8},
            ai_risk_level="low",
            ai_risk_score=0.25,
        )
        c2 = DailyCheckin.objects.create(
            patient=self.patient,
            checkin_date=date.today(),
            symptoms=["Cough", "Fever"],
            pain_level=4,
            vitals={"heart_rate": 84.0, "temperature_c": 38.1},
            ai_risk_level="medium",
            ai_risk_score=0.55,
        )

        # 2. Medication + Reminders
        med = Medication.objects.create(
            patient=self.patient,
            name="Metformin",
            dosage="500mg",
            frequency=Medication.Frequency.TWICE_DAILY,
            start_date=date.today() - timedelta(days=10),
            is_active=True,
        )
        log1 = MedicationReminderLog.objects.create(
            medication=med,
            scheduled_for=timezone.now() - timedelta(hours=4),
            acknowledged_at=timezone.now() - timedelta(hours=3),
        )

        # 3. Lab Test
        lab = LabTestRequest.objects.create(
            patient=self.patient,
            requested_by=self.doctor,
            test_name=LabTestRequest.TestName.HBA1C,
            priority=LabTestRequest.Priority.ROUTINE,
            status=LabTestRequest.Status.COMPLETED,
        )
        LabTestResult.objects.create(
            request=lab,
            result_text="HbA1c 6.5%",
            reviewed_at=timezone.now(),
        )

        # 4. Appointment
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_at=timezone.now() + timedelta(days=5),
            status=Appointment.Status.SCHEDULED,
            reason="Follow-up consultation",
        )

        payload = _serialize_patient_history_request(self.patient)

        self.assertEqual(payload["patient_id"], str(self.patient.id))
        self.assertEqual(len(payload["checkins"]), 2)
        self.assertEqual(payload["checkins"][0]["id"], c1.id)
        self.assertEqual(payload["checkins"][1]["id"], c2.id)
        self.assertEqual(payload["checkins"][0]["symptoms"], ["Cough", "Fatigue"])
        self.assertEqual(payload["checkins"][0]["vitals"]["heart_rate"], 72.0)

        self.assertEqual(len(payload["medications"]), 1)
        self.assertEqual(payload["medications"][0]["name"], "Metformin")
        self.assertEqual(payload["medications"][0]["frequency"], "twice_daily")

        self.assertEqual(len(payload["lab_tests"]), 1)
        self.assertEqual(payload["lab_tests"][0]["test_name"], "HBA1C")
        self.assertEqual(payload["lab_tests"][0]["status"], "completed")
        self.assertEqual(payload["lab_tests"][0]["result_text"], "HbA1c 6.5%")

        self.assertEqual(len(payload["appointments"]), 1)
        self.assertEqual(payload["appointments"][0]["reason"], "Follow-up consultation")

        self.assertEqual(len(payload["medication_reminder_logs"]), 1)
        self.assertEqual(payload["medication_reminder_logs"][0]["medication_id"], med.id)
        self.assertIsNotNone(payload["medication_reminder_logs"][0]["acknowledged_at"])
