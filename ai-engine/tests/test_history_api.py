"""End-to-end tests for the Phase 2 `/api/v1/history/summary` endpoint."""

from tests.factories import valid_history_request_payload


def test_history_summary_valid_payload_returns_200_and_valid_contract(client):
    payload = valid_history_request_payload()

    response = client.post("/api/v1/history/summary", json=payload)

    assert response.status_code == 200
    body = response.json()

    assert body["patient_id"] == payload["patient_id"]
    assert body["request_id"] == payload["request_id"]
    assert body["generated_at"]
    history = body["history"]
    assert history["checkin_count"] == 2
    assert history["latest_checkin"]["id"] == 2
    assert history["medications"][0]["name"] == "Lisinopril"
    assert history["latest_lab"]["id"] == 20
    assert history["open_follow_up"]["id"] == 30


def test_history_summary_rejects_missing_patient_id(client):
    payload = valid_history_request_payload()
    del payload["patient_id"]

    response = client.post("/api/v1/history/summary", json=payload)

    assert response.status_code == 422
    assert "errors" in response.json()


def test_history_summary_rejects_malformed_checkin(client):
    payload = valid_history_request_payload()
    payload["checkins"][0]["pain_level"] = "very high"  # not an int

    response = client.post("/api/v1/history/summary", json=payload)

    assert response.status_code == 422


def test_history_summary_handles_empty_history_lists(client):
    payload = valid_history_request_payload()
    payload["checkins"] = []
    payload["medications"] = []
    payload["lab_tests"] = []
    payload["appointments"] = []

    response = client.post("/api/v1/history/summary", json=payload)

    assert response.status_code == 200
    history = response.json()["history"]
    assert history["checkin_count"] == 0
    assert history["days_since_last_checkin"] is None
    assert history["latest_checkin"] is None
    assert history["medications"] == []
    assert history["latest_lab"] is None
    assert history["open_follow_up"] is None
    assert history["symptom_trend"]["trend"] == "insufficient_data"


def test_analyze_endpoint_still_works_unaffected_by_history_module(client):
    """Phase 1 regression guard: mounting the Phase 2 router must not change
    `/analyze` behavior."""
    from tests.factories import valid_request_payload

    response = client.post("/api/v1/analyze", json=valid_request_payload())
    assert response.status_code == 200
