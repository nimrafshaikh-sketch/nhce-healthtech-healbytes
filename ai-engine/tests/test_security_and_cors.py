"""Tests for internal service-to-service auth and CORS hardening."""

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def _valid_analyze_payload() -> dict:
    return {
        "patient_id": "1",
        "request_id": "req-sec-1",
        "timestamp": "2026-11-18T10:00:00Z",
        "check_in": {
            "symptoms": ["cough"],
            "severity": "mild",
            "duration": {"value": 1, "unit": "days"},
        },
        "medical_context": {"medical_history": [], "medication_adherence": []},
        "historical_context": {"previous_checkins": []},
    }


def _valid_lab_payload() -> dict:
    return {
        "patient_id": "1",
        "request_id": "lab-sec-1",
        "timestamp": "2026-11-18T10:00:00Z",
        "test_name": "HBA1C",
        "result_text": "HbA1c: 6.1%",
    }


def _valid_history_payload() -> dict:
    return {
        "patient_id": "1",
        "request_id": "hist-sec-1",
        "as_of": "2026-11-18T10:00:00Z",
        "checkins": [],
        "medications": [],
        "lab_tests": [],
        "appointments": [],
        "medication_reminder_logs": [],
    }


def test_internal_endpoints_require_matching_service_key_when_configured(monkeypatch):
    monkeypatch.setenv("AI_ENGINE_INTERNAL_KEY", "super-secret-internal-key")

    # Health check stays publicly reachable for container probes
    health_resp = client.get("/api/v1/health")
    assert health_resp.status_code == 200

    for path, payload in [
        ("/api/v1/analyze", _valid_analyze_payload()),
        ("/api/v1/lab-analysis", _valid_lab_payload()),
        ("/api/v1/history/summary", _valid_history_payload()),
    ]:
        missing = client.post(path, json=payload)
        assert missing.status_code == 401

        wrong = client.post(path, json=payload, headers={"X-Internal-Service-Key": "wrong-key"})
        assert wrong.status_code == 401

        valid = client.post(path, json=payload, headers={"X-Internal-Service-Key": "super-secret-internal-key"})
        assert valid.status_code == 200


def test_cors_excludes_wildcard_and_allows_configured_origins(monkeypatch):
    monkeypatch.setenv("AI_CORS_ALLOWED_ORIGINS", "*, http://localhost:5173 , https://clinic.example.com")
    assert "*" not in settings.cors_allowed_origins
    assert settings.cors_allowed_origins == ["http://localhost:5173", "https://clinic.example.com"]

    allowed_resp = client.options(
        "/api/v1/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert allowed_resp.headers.get("access-control-allow-origin") == "http://localhost:5173"

    disallowed_resp = client.options(
        "/api/v1/health",
        headers={
            "Origin": "https://untrusted.evil.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert disallowed_resp.headers.get("access-control-allow-origin") is None

