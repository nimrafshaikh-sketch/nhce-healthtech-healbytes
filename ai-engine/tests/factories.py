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


def valid_history_request_payload() -> dict:
    """Return a fresh, fully valid PatientHistoryRequest payload dict
    (Phase 2 - patient history summary) with a small, deterministic,
    stable-trend history."""

    return {
        "patient_id": "1",
        "request_id": "hist-req-001",
        "as_of": "2026-09-04T00:00:00+00:00",
        "checkins": [
            {
                "id": 1,
                "checkin_date": "2026-09-01",
                "symptoms": ["headache"],
                "mood": "tired",
                "pain_level": 3,
                "vitals": {"temperature_c": 37.0, "heart_rate": 72},
                "ai_risk_level": "low",
                "ai_risk_score": 0.2,
                "created_at": "2026-09-01T08:00:00+00:00",
            },
            {
                "id": 2,
                "checkin_date": "2026-09-03",
                "symptoms": ["headache"],
                "mood": "okay",
                "pain_level": 3,
                "vitals": {"temperature_c": 37.0, "heart_rate": 74},
                "ai_risk_level": "low",
                "ai_risk_score": 0.2,
                "created_at": "2026-09-03T08:00:00+00:00",
            },
        ],
        "medications": [
            {
                "id": 10,
                "name": "Lisinopril",
                "dosage": "10mg",
                "frequency": "once_daily",
                "start_date": "2026-08-01",
                "end_date": None,
                "is_active": True,
            }
        ],
        "lab_tests": [
            {
                "id": 20,
                "test_name": "CBC",
                "priority": "routine",
                "status": "completed",
                "result_text": "Within normal limits.",
                "result_date": "2026-09-02T09:00:00+00:00",
                "reviewed_at": "2026-09-02T10:00:00+00:00",
                "created_at": "2026-08-30T09:00:00+00:00",
            }
        ],
        "appointments": [
            {
                "id": 30,
                "scheduled_at": "2026-09-10T10:00:00+00:00",
                "status": "scheduled",
                "reason": "Follow-up",
            }
        ],
    }
