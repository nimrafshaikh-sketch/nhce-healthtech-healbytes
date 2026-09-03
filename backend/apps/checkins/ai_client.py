"""Client for the separate AI Engine service.

Agreed response contract (as of the notification-system spec):

    POST {AI_ENGINE_URL}/analyze/
    Request body:  {"checkin_id": int, "patient_id": int, "symptoms": [...],
                     "pain_level": int|null, "mood": str, "vitals": {...}, "notes": str}
    Response body: {
        "riskLevel": "low" | "medium" | "high",
        "riskScore": float,              # 0.0-1.0
        "reason": str,
        "recommendedAction": str,
        "notificationRecipient": str      # informational only, e.g. "doctor" | "caretaker" | "both" | "none"
    }

`notificationRecipient` is stored for reference/logging only - the backend
still decides who actually gets alerted/emailed via its own risk-level rule
(apps.alerts.rules), so the two systems can never disagree about routing.
Accepts "notification_recipient" or "recipient" as fallback keys in case the
AI engine's exact key casing differs, since that detail wasn't nailed down.

If AI_ENGINE_URL is not configured, the call fails, times out, or the
response is malformed, this returns risk_level="unavailable" rather than
raising - a check-in must always save successfully even if AI analysis
can't run.
"""
import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

VALID_RISK_LEVELS = {"low", "medium", "high"}

UNAVAILABLE_RESULT = {
    "risk_level": "unavailable",
    "risk_score": None,
    "reason": "",
    "recommended_action": "",
    "notification_recipient": "",
}


def _parse_response(data: dict) -> dict:
    risk_level = data.get("riskLevel")
    if risk_level not in VALID_RISK_LEVELS:
        return {**UNAVAILABLE_RESULT, "reason": "AI engine returned an unrecognized riskLevel."}

    risk_score = data.get("riskScore")
    if not isinstance(risk_score, (int, float)) or not (0.0 <= float(risk_score) <= 1.0):
        risk_score = None

    notification_recipient = (
        data.get("notificationRecipient")
        or data.get("notification_recipient")
        or data.get("recipient")
        or ""
    )

    return {
        "risk_level": risk_level,
        "risk_score": risk_score,
        "reason": data.get("reason", ""),
        "recommended_action": data.get("recommendedAction", ""),
        "notification_recipient": notification_recipient,
    }


def analyze_checkin(checkin) -> dict:
    if not settings.AI_ENGINE_URL:
        logger.info("AI_ENGINE_URL not configured; skipping AI analysis for checkin %s", checkin.id)
        return {**UNAVAILABLE_RESULT, "reason": "AI engine not configured."}

    payload = {
        "checkin_id": checkin.id,
        "patient_id": checkin.patient_id,
        "symptoms": checkin.symptoms,
        "pain_level": checkin.pain_level,
        "mood": checkin.mood,
        "vitals": checkin.vitals,
        "notes": checkin.notes,
    }
    try:
        response = requests.post(
            f"{settings.AI_ENGINE_URL.rstrip('/')}/analyze/",
            json=payload,
            timeout=settings.AI_ENGINE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        return _parse_response(data)
    except (requests.RequestException, ValueError) as exc:
        logger.warning("AI engine call failed for checkin %s: %s", checkin.id, exc)
        return {**UNAVAILABLE_RESULT, "reason": "AI engine call failed."}
