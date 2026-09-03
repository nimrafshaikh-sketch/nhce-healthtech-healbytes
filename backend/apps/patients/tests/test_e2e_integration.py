from datetime import date, timedelta
from unittest.mock import Mock, patch

from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.alerts.models import Alert
from apps.appointments.models import Appointment
from apps.checkins.models import DailyCheckin
from apps.core.test_utils import auth_headers, make_doctor, make_patient_user
from apps.labtests.models import LabTestRequest, LabTestResult
from apps.medications.models import Medication, MedicationReminderLog
from apps.patients.models import Patient


def simulate_ai_engine_analyze(url, json=None, **kwargs):
    """Simulates the FastAPI AI Engine /api/v1/analyze response."""
    check_in = json.get("check_in", {})
    symptoms = check_in.get("symptoms", [])
    has_severe = check_in.get("severity") == "severe"

    if has_severe or "Severe chest pain" in symptoms:
        risk_level = "High"
        risk_score = 87.0
        reason = "Severe chest pain reported with persistent symptoms and medication non-adherence. Historical check-ins indicate a worsening trend."
        alert_recipient = "physician"
        follow_up_action = "Prompt physician review is recommended based on the current risk assessment."
        explanation = "The assessment indicates High risk (score: 87.0/100) based on reported symptoms and medical history. Prompt physician review is recommended."
    else:
        risk_level = "Low"
        risk_score = 20.0
        reason = "Reported symptoms are mild and stable."
        alert_recipient = "none"
        follow_up_action = "Continue routine monitoring and complete the next scheduled check-in."
        explanation = "The assessment indicates Low risk (score: 20.0/100)."

    resp = Mock()
    resp.status_code = 200
    resp.json = lambda: {
        "request_id": json.get("request_id", "req_1"),
        "timestamp": timezone.now().isoformat(),
        "model_version": "rule-engine-v4",
        "risk_level": risk_level,
        "risk_score": risk_score,
        "reason": reason,
        "alert_recipient": alert_recipient,
        "follow_up_action": follow_up_action,
        "explanation": explanation,
    }
    resp.raise_for_status = lambda: None
    return resp


def simulate_ai_engine_history_summary(url, json=None, **kwargs):
    """Simulates the FastAPI AI Engine /api/v1/history/summary response."""
    checkins = json.get("checkins", [])
    medications = json.get("medications", [])
    labs = json.get("lab_tests", [])
    appointments = json.get("appointments", [])

    resp = Mock()
    resp.status_code = 200
    resp.json = lambda: {
        "request_id": json.get("request_id", "sum_1"),
        "timestamp": timezone.now().isoformat(),
        "history": {
            "checkin_count": len(checkins),
            "days_since_last_checkin": 1 if checkins else None,
            "latest_checkin": {
                "id": checkins[-1]["id"],
                "checkin_date": checkins[-1]["checkin_date"],
                "symptoms": checkins[-1]["symptoms"],
                "mood": checkins[-1].get("mood", ""),
                "pain_level": checkins[-1].get("pain_level"),
                "ai_risk_level": checkins[-1].get("ai_risk_level"),
            } if checkins else None,
            "symptom_trend": {
                "trend": "stable",
                "observed_checkins": len(checkins),
                "latest_symptom_count": 1,
                "previous_symptom_count": 1,
                "detail": "Reported symptom count is stable.",
            },
            "vital_trend": {},
            "medications": [
                {
                    "id": m["id"],
                    "name": m["name"],
                    "dosage": m["dosage"],
                    "frequency": m["frequency"],
                    "start_date": m["start_date"],
                    "end_date": m.get("end_date"),
                    "is_active": m["is_active"],
                } for m in medications
            ],
            "latest_lab": {
                "id": labs[0]["id"],
                "test_name": labs[0]["test_name"],
                "status": labs[0]["status"],
                "result_text": labs[0]["result_text"],
                "result_date": labs[0].get("result_date"),
                "reviewed": labs[0].get("reviewed_at") is not None,
            } if labs else None,
            "open_follow_up": {
                "id": appointments[0]["id"],
                "scheduled_at": appointments[0]["scheduled_at"],
                "status": appointments[0]["status"],
                "reason": appointments[0].get("reason", ""),
            } if appointments else None,
            "medication_adherence": {
                "overall_status": "adherent",
                "medications": [],
                "detail": "Adherence evaluated from reminder logs.",
            },
        },
    }
    resp.raise_for_status = lambda: None
    return resp


@override_settings(
    AI_ENGINE_URL="http://ai-engine.test",
    AI_ENGINE_TIMEOUT_SECONDS=5,
    CELERY_TASK_ALWAYS_EAGER=True,
    CELERY_TASK_EAGER_PROPAGATES=True,
)
class EndToEndAIIntegrationTests(APITestCase):
    def setUp(self):
        self.doctor = make_doctor(email="doc_e2e@example.com", username="doc_e2e")
        self.patient_user = make_patient_user(email="pat_e2e@example.com", username="pat_e2e")

        self.patient = Patient.objects.create(
            doctor=self.doctor,
            user=self.patient_user,
            full_name="E2E Patient",
            medical_notes="Hypertension\nAllergic to Sulfa",
            caretaker_name="John Doe",
            caretaker_email="caretaker@example.com",
        )

        self.doc_headers = auth_headers(self.doctor)
        self.pat_headers = auth_headers(self.patient_user)

    @patch("apps.checkins.ai_client.requests.post", side_effect=simulate_ai_engine_analyze)
    def test_full_checkin_analysis_flow_with_all_phases(self, mock_requests_post):
        # 1. Establish prior history (2 previous checkins)
        DailyCheckin.objects.create(
            patient=self.patient,
            checkin_date=date.today() - timedelta(days=2),
            symptoms=["Mild headache"],
            pain_level=2,
            ai_risk_level="low",
            ai_risk_score=0.20,
        )
        DailyCheckin.objects.create(
            patient=self.patient,
            checkin_date=date.today() - timedelta(days=1),
            symptoms=["Moderate headache"],
            pain_level=5,
            ai_risk_level="medium",
            ai_risk_score=0.50,
        )

        # 2. Add active medication with partial adherence
        med = Medication.objects.create(
            patient=self.patient,
            name="Amlodipine",
            dosage="5mg",
            frequency=Medication.Frequency.ONCE_DAILY,
            start_date=date.today() - timedelta(days=5),
            is_active=True,
        )
        MedicationReminderLog.objects.create(
            medication=med,
            scheduled_for=timezone.now() - timedelta(days=2),
            acknowledged_at=timezone.now() - timedelta(days=2),
        )
        MedicationReminderLog.objects.create(
            medication=med,
            scheduled_for=timezone.now() - timedelta(days=1),
            acknowledged_at=None,
        )

        # 3. Patient submits today's checkin via API
        payload = {
            "checkin_date": date.today().isoformat(),
            "symptoms": ["Severe chest pain", "Shortness of breath"],
            "pain_level": 8,
            "notes": "Feeling much worse today.",
        }
        resp = self.client.post(reverse("checkin-list-create"), payload, format="json", **self.pat_headers)
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)

        checkin_id = resp.data["id"]
        saved_checkin = DailyCheckin.objects.get(id=checkin_id)

        # Verify AI Engine computed risk and persisted it
        self.assertEqual(saved_checkin.ai_risk_level, "high")
        self.assertGreaterEqual(saved_checkin.ai_risk_score, 0.70)
        self.assertTrue(len(saved_checkin.ai_notes) > 0)
        self.assertTrue(len(saved_checkin.ai_recommended_action) > 0)

        # Verify outgoing payload contained rich context
        sent_payload = mock_requests_post.call_args.kwargs["json"]
        self.assertEqual(len(sent_payload["historical_context"]["previous_checkins"]), 2)
        self.assertEqual(sent_payload["medical_context"]["medical_history"], ["Hypertension", "Allergic to Sulfa"])
        self.assertEqual(len(sent_payload["medical_context"]["medication_adherence"]), 1)

        # Verify high-risk alert was automatically routed to doctor
        alert = Alert.objects.filter(patient=self.patient, checkin=saved_checkin).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.patient.doctor, self.doctor)
        self.assertEqual(alert.severity, Alert.Severity.HIGH)

    @patch("apps.checkins.ai_client.requests.post", side_effect=simulate_ai_engine_history_summary)
    def test_full_doctor_and_patient_ai_summary_flow(self, mock_requests_post):
        # 1. Add checkin
        DailyCheckin.objects.create(
            patient=self.patient,
            checkin_date=date.today() - timedelta(days=1),
            symptoms=["Fatigue"],
            pain_level=3,
            vitals={"heart_rate": 76.0},
            ai_risk_level="low",
            ai_risk_score=0.25,
        )

        # 2. Add lab test
        lab = LabTestRequest.objects.create(
            patient=self.patient,
            requested_by=self.doctor,
            test_name=LabTestRequest.TestName.CBC,
            status=LabTestRequest.Status.COMPLETED,
        )
        LabTestResult.objects.create(
            request=lab,
            result_text="WBC normal, Platelets normal",
            reviewed_at=timezone.now(),
        )

        # 3. Add appointment
        Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            scheduled_at=timezone.now() + timedelta(days=3),
            status=Appointment.Status.SCHEDULED,
            reason="Routine checkup",
        )

        # 4. Doctor fetches AI summary
        doc_url = reverse("analytics-patient-ai-summary", args=[self.patient.id])
        doc_resp = self.client.get(doc_url, **self.doc_headers)
        self.assertEqual(doc_resp.status_code, status.HTTP_200_OK)

        history = doc_resp.data["history"]
        self.assertEqual(history["checkin_count"], 1)
        self.assertEqual(history["latest_lab"]["test_name"], "CBC")
        self.assertEqual(history["latest_lab"]["result_text"], "WBC normal, Platelets normal")
        self.assertIsNotNone(history["open_follow_up"])
        self.assertEqual(history["open_follow_up"]["reason"], "Routine checkup")

        # 5. Patient fetches own AI summary
        pat_url = reverse("analytics-me-ai-summary")
        pat_resp = self.client.get(pat_url, **self.pat_headers)
        self.assertEqual(pat_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(pat_resp.data["history"]["checkin_count"], 1)
