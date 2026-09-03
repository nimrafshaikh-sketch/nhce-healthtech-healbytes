"""End-to-end contract tests for the FastAPI application (Phase 1 baseline +
Phase 2 bounded historical-trend adjustment + Phase 3 bounded
medication-adherence adjustment + Phase 4 deterministic follow-up recommendation)."""

from app.analysis.follow_up_recommender import (
    FOLLOW_UP_RECOMMENDATIONS,
    recommend_follow_up,
)
from app.analysis.risk_engine import MODEL_VERSION
from app.schemas.common import AlertRecipient, RiskLevel
from tests.factories import valid_request_payload


def test_health_check(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_valid_payload_returns_200_and_valid_contract(client):
    payload = valid_request_payload()

    response = client.post("/api/v1/analyze", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert body["request_id"] == payload["request_id"]
    assert body["timestamp"]
    assert body["risk_level"] in {level.value for level in RiskLevel}
    assert isinstance(body["risk_score"], (int, float))
    assert 0 <= body["risk_score"] <= 100
    assert isinstance(body["reason"], str) and body["reason"]
    assert body["alert_recipient"] in {recipient.value for recipient in AlertRecipient}
    assert body["follow_up_action"] == recommend_follow_up(RiskLevel(body["risk_level"]))
    assert isinstance(body["explanation"], str) and body["explanation"]
    assert body["model_version"] == MODEL_VERSION


def test_analyze_rejects_invalid_payload(client):
    payload = valid_request_payload()
    del payload["patient_id"]

    response = client.post("/api/v1/analyze", json=payload)

    assert response.status_code == 422
    assert "errors" in response.json()


def test_analyze_alert_recipient_matches_phase1_mapping(client):
    response = client.post("/api/v1/analyze", json=valid_request_payload())
    body = response.json()

    expected_recipient_by_level = {
        "Low": "none",
        "Medium": "care_team",
        "High": "physician",
    }
    assert body["alert_recipient"] == expected_recipient_by_level[body["risk_level"]]
    assert body["alert_recipient"] != "emergency_services"


def test_analyze_is_deterministic_across_repeated_requests(client):
    payload = valid_request_payload()

    first = client.post("/api/v1/analyze", json=payload).json()
    second = client.post("/api/v1/analyze", json=payload).json()

    assert first["risk_score"] == second["risk_score"]
    assert first["risk_level"] == second["risk_level"]
    assert first["reason"] == second["reason"]
    assert first["alert_recipient"] == second["alert_recipient"]
    assert first["follow_up_action"] == second["follow_up_action"]


def test_analyze_reflects_historical_trend_in_reason(client):
    # The default factory payload has exactly one previous check-in, which
    # is intentionally insufficient evidence for a directional trend.
    payload = valid_request_payload()

    response = client.post("/api/v1/analyze", json=payload)

    assert response.status_code == 200
    assert "insufficient_data" in response.json()["reason"].lower()


def test_analyze_non_adherent_medication_increases_score_and_is_reflected_in_reason(client):
    adherent_payload = valid_request_payload()
    adherent_payload["medical_context"]["medication_adherence"] = [
        {"medication_name": "Lisinopril", "adherence_status": "adherent"}
    ]

    non_adherent_payload = valid_request_payload()
    non_adherent_payload["medical_context"]["medication_adherence"] = [
        {"medication_name": "Lisinopril", "adherence_status": "non_adherent"}
    ]

    adherent_body = client.post("/api/v1/analyze", json=adherent_payload).json()
    non_adherent_body = client.post("/api/v1/analyze", json=non_adherent_payload).json()

    assert non_adherent_body["risk_score"] == adherent_body["risk_score"] + 5
    assert "medication-adherence record" in non_adherent_body["reason"].lower()
    assert "does not establish medical risk" in non_adherent_body["reason"].lower()


def test_analyze_unknown_medication_does_not_penalize(client):
    unknown_payload = valid_request_payload()
    unknown_payload["medical_context"]["medication_adherence"] = [
        {"medication_name": "Lisinopril", "adherence_status": "unknown"}
    ]

    adherent_payload = valid_request_payload()
    adherent_payload["medical_context"]["medication_adherence"] = [
        {"medication_name": "Lisinopril", "adherence_status": "adherent"}
    ]

    unknown_body = client.post("/api/v1/analyze", json=unknown_payload).json()
    adherent_body = client.post("/api/v1/analyze", json=adherent_payload).json()

    assert unknown_body["risk_score"] == adherent_body["risk_score"]


# --- Phase 4 follow-up recommendation API tests ------------------------------


def test_analyze_low_risk_scenario_returns_routine_monitoring_action(client):
    payload = valid_request_payload()
    payload["medical_context"]["medical_history"] = []
    payload["medical_context"]["medication_adherence"] = []
    payload["historical_context"]["previous_checkins"] = []
    payload["check_in"] = {
        "symptoms": ["mild headache"],
        "severity": "mild",
        "duration": {"value": 2, "unit": "hours"},
    }

    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["risk_level"] == "Low"
    assert body["follow_up_action"] == FOLLOW_UP_RECOMMENDATIONS[RiskLevel.LOW]
    assert "routine monitoring" in body["follow_up_action"].lower()


def test_analyze_medium_risk_scenario_returns_care_team_review_action(client):
    payload = valid_request_payload()
    payload["medical_context"]["medical_history"] = []
    payload["medical_context"]["medication_adherence"] = []
    payload["historical_context"]["previous_checkins"] = []
    payload["check_in"] = {
        "symptoms": ["headache", "fatigue"],
        "severity": "moderate",
        "duration": {"value": 2, "unit": "days"},
    }

    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["risk_level"] == "Medium"
    assert body["follow_up_action"] == FOLLOW_UP_RECOMMENDATIONS[RiskLevel.MEDIUM]
    assert "care-team review" in body["follow_up_action"].lower()


def test_analyze_high_risk_scenario_returns_physician_review_action(client):
    payload = valid_request_payload()
    payload["medical_context"]["medical_history"] = ["asthma"]
    payload["medical_context"]["medication_adherence"] = []
    payload["historical_context"]["previous_checkins"] = []
    payload["check_in"] = {
        "symptoms": ["chest pain", "shortness of breath", "dizziness", "fatigue"],
        "severity": "severe",
        "duration": {"value": 2, "unit": "weeks"},
    }

    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["risk_level"] == "High"
    assert body["follow_up_action"] == FOLLOW_UP_RECOMMENDATIONS[RiskLevel.HIGH]
    assert "physician review" in body["follow_up_action"].lower()
    assert "emergency" not in body["follow_up_action"].lower()


# --- Phase 5 explanation layer API tests -------------------------------------


def test_analyze_low_risk_scenario_returns_explanation(client):
    payload = valid_request_payload()
    payload["medical_context"]["medical_history"] = []
    payload["medical_context"]["medication_adherence"] = []
    payload["historical_context"]["previous_checkins"] = []
    payload["check_in"] = {
        "symptoms": ["mild headache"],
        "severity": "mild",
        "duration": {"value": 2, "unit": "hours"},
    }

    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["risk_level"] == "Low"
    assert body["risk_score"] == 15.0
    assert isinstance(body["explanation"], str) and body["explanation"]
    assert "Low risk" in body["explanation"]
    assert "(score: 15.0/100)" in body["explanation"]
    assert body["model_version"] == MODEL_VERSION


def test_analyze_medium_risk_scenario_returns_explanation(client):
    payload = valid_request_payload()
    payload["medical_context"]["medical_history"] = []
    payload["medical_context"]["medication_adherence"] = []
    payload["historical_context"]["previous_checkins"] = []
    payload["check_in"] = {
        "symptoms": ["headache", "fatigue"],
        "severity": "moderate",
        "duration": {"value": 2, "unit": "days"},
    }

    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["risk_level"] == "Medium"
    assert body["risk_score"] == 60.0
    assert isinstance(body["explanation"], str) and body["explanation"]
    assert "Medium risk" in body["explanation"]
    assert "(score: 60.0/100)" in body["explanation"]
    assert body["model_version"] == MODEL_VERSION


def test_analyze_high_risk_scenario_returns_explanation(client):
    payload = valid_request_payload()
    payload["medical_context"]["medical_history"] = ["asthma"]
    payload["medical_context"]["medication_adherence"] = []
    payload["historical_context"]["previous_checkins"] = []
    payload["check_in"] = {
        "symptoms": ["chest pain", "shortness of breath", "dizziness", "fatigue"],
        "severity": "severe",
        "duration": {"value": 2, "unit": "weeks"},
    }

    response = client.post("/api/v1/analyze", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["risk_level"] == "High"
    assert body["risk_score"] == 100.0
    assert isinstance(body["explanation"], str) and body["explanation"]
    assert "High risk" in body["explanation"]
    assert "(score: 100.0/100)" in body["explanation"]
    assert "emergency" not in body["explanation"].lower()
    assert body["model_version"] == MODEL_VERSION


def test_analyze_provider_failure_returns_200_with_fallback_explanation(client, monkeypatch):
    class ExplodingProvider:
        def generate_explanation(self, *args, **kwargs):
            raise ConnectionError("LLM upstream provider timeout")

    from app.analysis import explanation_service
    from app.analysis.explanation_service import ExplanationService

    failing_service = ExplanationService(provider=ExplodingProvider())
    monkeypatch.setattr(explanation_service, "_default_explanation_service", failing_service)

    payload = valid_request_payload()
    response = client.post("/api/v1/analyze", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert body["risk_level"] == "Medium"
    assert body["risk_score"] == 65.0
    assert isinstance(body["explanation"], str) and body["explanation"]
    assert "Medium risk" in body["explanation"]
    assert "(score: 65.0/100)" in body["explanation"]
    assert body["follow_up_action"] == FOLLOW_UP_RECOMMENDATIONS[RiskLevel.MEDIUM]
    assert body["alert_recipient"] == "care_team"
    assert body["model_version"] == MODEL_VERSION
