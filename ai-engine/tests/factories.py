"""Reusable valid payload builders for contract tests."""

from datetime import datetime, timezone


def valid_request_payload() -> dict:
    """Return a fresh, fully valid AIAnalysisRequest payload dict."""

    now = datetime.now(timezone.utc).isoformat()
    return {
        "patient_id": "patient-001",
        "request_id": "req-001",
        "timestamp": now,
        "check_in": {
            "symptoms": ["headache", "fatigue"],
            "severity": "moderate",
            "duration": {"value": 2, "unit": "days"},
        },
        "medical_context": {
            "medical_history": ["hypertension"],
            "medication_adherence": [
                {"medication_name": "Lisinopril", "adherence_status": "adherent"}
            ],
        },
        "historical_context": {
            "previous_checkins": [
                {
                    "request_id": "req-000",
                    "timestamp": now,
                    "severity": "mild",
                    "risk_level": "Low",
                }
            ]
        },
    }


def valid_response_payload() -> dict:
    """Return a fresh, fully valid AIAnalysisResponse payload dict."""

    return {
        "request_id": "req-001",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "risk_level": "Medium",
        "risk_score": 42.5,
        "reason": "Symptom severity trending upward.",
        "alert_recipient": "care_team",
        "follow_up_action": "Schedule a nurse call within 24 hours.",
        "model_version": "0.0.0-unimplemented",
    }
