"""End-to-end contract tests for the FastAPI application (Phase 6: exact
route and payload shape from `backend/apps/checkins/ai_client.py`,
`feature/backend` branch)."""

from app.analysis.risk_engine import MODEL_VERSION
from app.schemas.common import NotificationRecipient, RiskLevel
from tests.factories import valid_request_payload


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analyze_valid_payload_returns_200_and_valid_contract(client):
    payload = valid_request_payload()

    response = client.post("/analyze/", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert set(body.keys()) == {
        "riskLevel",
        "riskScore",
        "reason",
        "recommendedAction",
        "notificationRecipient",
    }
    assert body["riskLevel"] in {level.value for level in RiskLevel}
    assert isinstance(body["riskScore"], (int, float))
    assert 0.0 <= body["riskScore"] <= 1.0
    assert isinstance(body["reason"], str) and body["reason"]
    assert isinstance(body["recommendedAction"], str) and body["recommendedAction"]
    assert body["notificationRecipient"] in {r.value for r in NotificationRecipient}


def test_analyze_without_trailing_slash_is_not_found(client):
    # ai_client.py always calls with a trailing slash; verify the exact
    # route rather than relying on FastAPI's redirect behavior.
    response = client.post("/analyze", json=valid_request_payload(), follow_redirects=False)
    assert response.status_code in (307, 404)


def test_analyze_rejects_invalid_payload(client):
    payload = valid_request_payload()
    del payload["patient_id"]

    response = client.post("/analyze/", json=payload)

    assert response.status_code == 422
    assert "errors" in response.json()


def test_analyze_rejects_insufficient_data(client):
    # Neither symptoms nor a pain level: nothing to safely score. Rejected
    # up front rather than fabricating a risk score.
    payload = valid_request_payload()
    payload["symptoms"] = []
    payload["pain_level"] = None

    response = client.post("/analyze/", json=payload)

    assert response.status_code == 422


def test_analyze_is_deterministic_across_repeated_requests(client):
    payload = valid_request_payload()

    first = client.post("/analyze/", json=payload).json()
    second = client.post("/analyze/", json=payload).json()

    assert first == second


def test_analyze_low_risk_scenario(client):
    payload = valid_request_payload()
    payload["symptoms"] = ["mild headache"]
    payload["pain_level"] = 1

    response = client.post("/analyze/", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["riskLevel"] == "low"
    assert body["notificationRecipient"] == "none"


def test_analyze_medium_risk_scenario(client):
    payload = valid_request_payload()
    payload["symptoms"] = ["headache", "fatigue"]
    payload["pain_level"] = 5

    response = client.post("/analyze/", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["riskLevel"] == "medium"
    assert body["notificationRecipient"] == "caretaker"


def test_analyze_high_risk_scenario(client):
    payload = valid_request_payload()
    payload["symptoms"] = ["chest pain", "shortness of breath", "dizziness", "fatigue"]
    payload["pain_level"] = 9

    response = client.post("/analyze/", json=payload)
    assert response.status_code == 200
    body = response.json()

    assert body["riskLevel"] == "high"
    assert body["notificationRecipient"] == "doctor"
    assert "emergency" not in body["recommendedAction"].lower()


def test_analyze_accepts_empty_mood_string(client):
    # Django's `mood = models.CharField(max_length=50, blank=True)` sends an
    # unset mood as "" (not null); this must be accepted, not rejected.
    payload = valid_request_payload()
    payload["mood"] = ""

    response = client.post("/analyze/", json=payload)

    assert response.status_code == 200


def test_analyze_pain_level_out_of_range_is_rejected(client):
    payload = valid_request_payload()
    payload["pain_level"] = 11

    response = client.post("/analyze/", json=payload)
    assert response.status_code == 422


def test_analyze_malformed_json_is_rejected(client):
    response = client.post(
        "/analyze/", content="{not valid json", headers={"Content-Type": "application/json"}
    )
    assert response.status_code == 422
