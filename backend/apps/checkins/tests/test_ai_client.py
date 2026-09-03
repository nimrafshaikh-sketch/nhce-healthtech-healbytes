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
class AIClientResponseParsingTests(TestCase):
    @patch("apps.checkins.ai_client.requests.post")
    def test_valid_camelcase_response_parsed(self, mock_post):
        mock_post.return_value = Mock(
            status_code=200,
            json=lambda: {
                "riskLevel": "high", "riskScore": 0.87, "reason": "fever + high pain",
                "recommendedAction": "see a doctor today", "notificationRecipient": "doctor",
            },
        )
        mock_post.return_value.raise_for_status = lambda: None
        result = analyze_checkin(FakeCheckin())
        self.assertEqual(result["risk_level"], "high")
        self.assertEqual(result["risk_score"], 0.87)
        self.assertEqual(result["reason"], "fever + high pain")
        self.assertEqual(result["recommended_action"], "see a doctor today")
        self.assertEqual(result["notification_recipient"], "doctor")

    @patch("apps.checkins.ai_client.requests.post")
    def test_invalid_risk_level_falls_back_to_unavailable(self, mock_post):
        mock_post.return_value = Mock(status_code=200, json=lambda: {"riskLevel": "critical"})
        mock_post.return_value.raise_for_status = lambda: None
        result = analyze_checkin(FakeCheckin())
        self.assertEqual(result["risk_level"], "unavailable")

    @patch("apps.checkins.ai_client.requests.post")
    def test_out_of_range_risk_score_is_discarded(self, mock_post):
        mock_post.return_value = Mock(status_code=200, json=lambda: {"riskLevel": "low", "riskScore": 5.0})
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
