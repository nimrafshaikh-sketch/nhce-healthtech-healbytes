from datetime import date, timedelta
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.checkins.ai_client import (
    _build_historical_context,
    _build_medical_context,
    _build_request_payload,
    analyze_checkin,
    get_patient_history_summary,
)
from apps.checkins.models import DailyCheckin
from apps.core.test_utils import make_doctor
from apps.medications.models import Medication, MedicationReminderLog
from apps.patients.models import Patient


class FakeCheckin:
    id = 1
    patient_id = 1
    patient = None
    symptoms = ["cough"]
    pain_level = 3
    mood = "tired"
    vitals = {}
    notes = ""


class AIClientNoUrlTests(TestCase):
    @override_settings(AI_ENGINE_URL="")
    def test_no_url_configured_returns_unavailable(self):
        result = analyze_checkin(FakeCheckin())
        self.assertEqual(result["risk_level"], "unavailable")
        self.assertIsNone(result["risk_score"])


@override_settings(AI_ENGINE_URL="http://ai-engine.local", AI_ENGINE_TIMEOUT_SECONDS=1)
class AIClientNoSymptomsTests(TestCase):
    def test_no_symptoms_skips_call_returns_unavailable(self):
        class NoSymptomsCheckin(FakeCheckin):
            symptoms = []

        with patch("apps.checkins.ai_client.requests.post") as mock_post:
            result = analyze_checkin(NoSymptomsCheckin())
            mock_post.assert_not_called()
        self.assertEqual(result["risk_level"], "unavailable")
        self.assertIsNone(result["risk_score"])


@override_settings(AI_ENGINE_URL="http://ai-engine.local", AI_ENGINE_TIMEOUT_SECONDS=1)
class AIClientResponseParsingTests(TestCase):
    @patch("apps.checkins.ai_client.requests.post")
    def test_calls_existing_ai_engine_endpoint_with_contract_shaped_payload(self, mock_post):
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "risk_level": "High",
                "risk_score": 87.0,
                "reason": "fever + high pain",
                "alert_recipient": "physician",
                "follow_up_action": "see a doctor today",
            },
        )
        mock_post.return_value.raise_for_status = lambda: None
        analyze_checkin(FakeCheckin())

        called_url = mock_post.call_args.args[0]
        self.assertTrue(called_url.endswith("/api/v1/analyze"))
        sent_payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(sent_payload["patient_id"], "1")
        self.assertEqual(sent_payload["request_id"], "1")
        self.assertEqual(sent_payload["check_in"]["symptoms"], ["cough"])
        self.assertEqual(sent_payload["check_in"]["severity"], "mild")
        self.assertIn("duration", sent_payload["check_in"])
        self.assertIn("medical_context", sent_payload)
        self.assertIn("historical_context", sent_payload)

    @patch("apps.checkins.ai_client.requests.post")
    def test_valid_snake_case_0_100_response_parsed(self, mock_post):
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "risk_level": "High",
                "risk_score": 87.0,
                "reason": "fever + high pain",
                "alert_recipient": "physician",
                "follow_up_action": "see a doctor today",
            },
        )
        mock_post.return_value.raise_for_status = lambda: None
        result = analyze_checkin(FakeCheckin())
        self.assertEqual(result["risk_level"], "high")
        self.assertEqual(result["risk_score"], 0.87)
        self.assertEqual(result["reason"], "fever + high pain")
        self.assertEqual(result["recommended_action"], "see a doctor today")
        self.assertEqual(result["notification_recipient"], "physician")

    @patch("apps.checkins.ai_client.requests.post")
    def test_invalid_risk_level_falls_back_to_unavailable(self, mock_post):
        mock_post.return_value = Mock(status_code=200, json=lambda: {"risk_level": "critical"})
        mock_post.return_value.raise_for_status = lambda: None
        result = analyze_checkin(FakeCheckin())
        self.assertEqual(result["risk_level"], "unavailable")

    @patch("apps.checkins.ai_client.requests.post")
    def test_out_of_range_risk_score_is_discarded(self, mock_post):
        mock_post.return_value = Mock(
            status_code=200, json=lambda: {"risk_level": "Low", "risk_score": 150.0}
        )
        mock_post.return_value.raise_for_status = lambda: None
        result = analyze_checkin(FakeCheckin())
        self.assertEqual(result["risk_level"], "low")
        self.assertIsNone(result["risk_score"])

    @patch("apps.checkins.ai_client.requests.post")
    def test_request_exception_returns_unavailable(self, mock_post):
        import requests
        mock_post.side_effect = requests.ConnectionError("boom")
        result = analyze_checkin(FakeCheckin())
        self.assertEqual(result["risk_level"], "unavailable")


class AIClientRichContextTests(TestCase):
    def setUp(self):
        self.doctor = make_doctor()
        self.patient = Patient.objects.create(
            doctor=self.doctor,
            full_name="Context Patient",
            medical_notes="Hypertension\nType 2 Diabetes",
        )

    def test_medical_context_assembly(self):
        med1 = Medication.objects.create(
            patient=self.patient,
            name="Lisinopril",
            dosage="10mg",
            frequency=Medication.Frequency.ONCE_DAILY,
            start_date=date.today() - timedelta(days=30),
            is_active=True,
        )
        # 3 sent reminders, 3 acknowledged -> adherent
        for i in range(3):
            MedicationReminderLog.objects.create(
                medication=med1,
                scheduled_for=timezone.now() - timedelta(days=i + 1),
                acknowledged_at=timezone.now() - timedelta(days=i + 1, hours=-1),
            )

        med2 = Medication.objects.create(
            patient=self.patient,
            name="Metformin",
            dosage="500mg",
            frequency=Medication.Frequency.TWICE_DAILY,
            start_date=date.today() - timedelta(days=10),
            is_active=True,
        )
        # 0 reminder logs -> unknown

        ctx = _build_medical_context(self.patient)
        self.assertEqual(ctx["medical_history"], ["Hypertension", "Type 2 Diabetes"])
        self.assertEqual(len(ctx["medication_adherence"]), 2)

        adherence_map = {m["medication_name"]: m for m in ctx["medication_adherence"]}
        self.assertEqual(adherence_map["Lisinopril"]["adherence_status"], "adherent")
        self.assertIsNotNone(adherence_map["Lisinopril"]["last_taken"])
        self.assertEqual(adherence_map["Metformin"]["adherence_status"], "unknown")
        self.assertIsNone(adherence_map["Metformin"]["last_taken"])

    def test_historical_context_assembly(self):
        # Create 2 previous checkins
        c1 = DailyCheckin.objects.create(
            patient=self.patient,
            checkin_date=date.today() - timedelta(days=2),
            symptoms=["Mild headache"],
            pain_level=2,
            ai_risk_level="low",
        )
        c2 = DailyCheckin.objects.create(
            patient=self.patient,
            checkin_date=date.today() - timedelta(days=1),
            symptoms=["Moderate headache"],
            pain_level=5,
            ai_risk_level="medium",
        )
        current = DailyCheckin.objects.create(
            patient=self.patient,
            checkin_date=date.today(),
            symptoms=["Severe headache"],
            pain_level=8,
        )

        hist = _build_historical_context(current)
        prev_list = hist["previous_checkins"]
        self.assertEqual(len(prev_list), 2)
        # Chronological order
        self.assertEqual(prev_list[0]["request_id"], str(c1.id))
        self.assertEqual(prev_list[0]["severity"], "mild")
        self.assertEqual(prev_list[0]["risk_level"], "Low")
        self.assertEqual(prev_list[1]["request_id"], str(c2.id))
        self.assertEqual(prev_list[1]["severity"], "moderate")
        self.assertEqual(prev_list[1]["risk_level"], "Medium")

    @override_settings(AI_ENGINE_URL="http://ai-engine.local", AI_ENGINE_TIMEOUT_SECONDS=2)
    @patch("apps.checkins.ai_client.requests.post")
    def test_get_patient_history_summary_success(self, mock_post):
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "request_id": "sum_1",
                "timestamp": timezone.now().isoformat(),
                "history": {"checkin_count": 0},
            },
        )
        mock_post.return_value.raise_for_status = lambda: None

        res = get_patient_history_summary(self.patient)
        self.assertIsNotNone(res)
        self.assertEqual(res["request_id"], "sum_1")
        called_url = mock_post.call_args.args[0]
        self.assertTrue(called_url.endswith("/api/v1/history/summary"))
