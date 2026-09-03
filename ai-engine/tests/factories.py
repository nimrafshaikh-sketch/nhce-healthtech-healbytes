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
