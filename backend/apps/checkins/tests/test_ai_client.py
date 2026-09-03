from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from apps.checkins.ai_client import analyze_checkin


class FakeCheckin:
    id = 1
    patient_id = 1
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
        # The AI Engine's check_in.symptoms contract requires at least one
        # entry (min_length=1); a check-in with none reported must not
        # fabricate one, and must not call the AI Engine at all.
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
        # Locks in the fix: the AI Engine's actual, existing route is
        # POST /api/v1/analyze (see ai-engine/app/config.py api_prefix +
        # app/api/routes.py), not "/analyze/".
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "risk_level": "High", "risk_score": 87.0, "reason": "fever + high pain",
                "alert_recipient": "physician", "follow_up_action": "see a doctor today",
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
        self.assertEqual(sent_payload["check_in"]["severity"], "mild")  # pain_level=3
        self.assertIn("duration", sent_payload["check_in"])

    @patch("apps.checkins.ai_client.requests.post")
    def test_valid_snake_case_0_100_response_parsed(self, mock_post):
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "risk_level": "High", "risk_score": 87.0, "reason": "fever + high pain",
                "alert_recipient": "physician", "follow_up_action": "see a doctor today",
            },
        )
        mock_post.return_value.raise_for_status = lambda: None
        result = analyze_checkin(FakeCheckin())
        self.assertEqual(result["risk_level"], "high")
        self.assertEqual(result["risk_score"], 0.87)  # normalized from the AI Engine's 0-100 scale
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
