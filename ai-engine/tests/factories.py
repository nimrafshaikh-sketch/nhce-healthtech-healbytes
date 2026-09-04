"""Reusable valid payload builders for contract tests.

Shapes match the agreed backend wire contract exactly (see
`backend/apps/checkins/ai_client.py` on the `feature/backend` branch).
"""


def valid_request_payload() -> dict:
    """Return a fresh, fully valid AIAnalysisRequest payload dict."""

    return {
        "checkin_id": 1,
        "patient_id": 1,
        "symptoms": ["headache", "fatigue"],
        "pain_level": 4,
        "mood": "anxious",
        "vitals": {"heart_rate": 78, "temperature_c": 37.1},
        "notes": "Patient reports gradual onset since yesterday.",
    }


def valid_response_payload() -> dict:
    """Return a fresh, fully valid AIAnalysisResponse payload dict."""

    return {
        "riskLevel": "medium",
        "riskScore": 0.425,
        "reason": "Symptom severity trending upward.",
        "recommendedAction": "Care-team review and closer follow-up are recommended.",
        "notificationRecipient": "caretaker",
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
