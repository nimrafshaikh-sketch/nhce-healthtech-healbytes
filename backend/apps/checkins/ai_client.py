"""Client for the separate AI Engine service.

Integration contract (matches the AI Engine's existing, fixed schemas - see
ai-engine/app/schemas/request.py and response.py, unchanged by this file):

    POST {AI_ENGINE_URL}/api/v1/analyze
    Request body (AIAnalysisRequest):
        {"patient_id": str, "request_id": str, "timestamp": ISO datetime,
         "check_in": {"symptoms": [str, ...],
                       "severity": "mild" | "moderate" | "severe",
                       "duration": {"value": int, "unit": "hours"|"days"|"weeks"}}}
        (medical_context / historical_context are optional on the AI Engine
        side - both default to empty there - and are not populated by this
        integration; only the current check-in is analyzed.)
    Response body (AIAnalysisResponse):
        {"risk_level": "Low"|"Medium"|"High", "risk_score": float (0-100),
         "reason": str,
         "alert_recipient": "none"|"care_team"|"physician"|"emergency_services",
         "follow_up_action": str|null, "explanation": str|null,
         "model_version": str, "request_id": str, "timestamp": ISO datetime}

Compatibility shims (integration boundary only - the DailyCheckin model and
the AI Engine's contract are both left unchanged):
  - severity is derived from the self-reported 0-10 pain_level using a
    standard clinical pain-scale banding (0-3 mild, 4-6 moderate,
    7-10 severe); a missing pain_level defaults to "moderate".
  - duration: the check-in form has no notion of symptom duration, but the
    AI Engine's contract requires one. Since this is a same-day daily
    check-in, a fixed 1-day duration is sent. This is a documented
    placeholder, not data collected from the patient.
  - explanation and model_version are returned by the AI Engine but not
    persisted - DailyCheckin has no field for them and this integration
    fix does not add one (see project scope).

This function's *return* shape is the existing internal contract other code
depends on (apps.checkins.tasks, apps.alerts.rules, and the DailyCheckin
model's ai_risk_level choices / ai_risk_score validators) and is UNCHANGED:
    {"risk_level": "low"|"medium"|"high"|"unavailable",
     "risk_score": float 0.0-1.0 or None,
     "reason": str, "recommended_action": str, "notification_recipient": str}
risk_level is lowercased and risk_score is normalized from the AI Engine's
0-100 scale to the model's existing 0.0-1.0 range.

If AI_ENGINE_URL is not configured, there are no symptoms to analyze, the
call fails, times out, or the response is malformed, this returns
risk_level="unavailable" rather than raising - a check-in must always save
successfully even if AI analysis can't run.
"""
import logging

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

VALID_RISK_LEVELS = {"Low", "Medium", "High"}

ANALYZE_PATH = "/api/v1/analyze"

UNAVAILABLE_RESULT = {
    "risk_level": "unavailable",
    "risk_score": None,
    "reason": "",
    "recommended_action": "",
    "notification_recipient": "",
}


def _severity_from_pain_level(pain_level):
    """Map the self-reported 0-10 pain_level to the AI Engine's SeverityLevel
    using a standard clinical pain-scale banding. No pain_level recorded ->
    neutral "moderate" default (not "mild", so missing data isn't treated as
    reassuring)."""
    if pain_level is None:
        return "moderate"
    if pain_level <= 3:
        return "mild"
    if pain_level <= 6:
        return "moderate"
    return "severe"


def _build_request_payload(checkin) -> dict:
    return {
        "patient_id": str(checkin.patient_id),
        "request_id": str(checkin.id),
        "timestamp": timezone.now().isoformat(),
        "check_in": {
            "symptoms": list(checkin.symptoms),
            "severity": _severity_from_pain_level(checkin.pain_level),
            "duration": {"value": 1, "unit": "days"},
        },
    }


def _parse_response(data: dict) -> dict:
    risk_level = data.get("risk_level")
    if risk_level not in VALID_RISK_LEVELS:
        return {**UNAVAILABLE_RESULT, "reason": "AI engine returned an unrecognized risk_level."}

    risk_score_0_100 = data.get("risk_score")
    if isinstance(risk_score_0_100, (int, float)) and not isinstance(risk_score_0_100, bool) and (
        0.0 <= float(risk_score_0_100) <= 100.0
    ):
        risk_score = float(risk_score_0_100) / 100.0
    else:
        risk_score = None

    return {
        "risk_level": risk_level.lower(),
        "risk_score": risk_score,
        "reason": data.get("reason") or "",
        "recommended_action": data.get("follow_up_action") or "",
        "notification_recipient": data.get("alert_recipient") or "",
    }


def analyze_checkin(checkin) -> dict:
    if not settings.AI_ENGINE_URL:
        logger.info("AI_ENGINE_URL not configured; skipping AI analysis for checkin %s", checkin.id)
        return {**UNAVAILABLE_RESULT, "reason": "AI engine not configured."}

    if not checkin.symptoms:
        # The AI Engine's contract requires at least one reported symptom;
        # skip the call rather than fabricating one.
        logger.info("Checkin %s has no symptoms reported; skipping AI analysis.", checkin.id)
        return {**UNAVAILABLE_RESULT, "reason": "No symptoms reported; AI analysis skipped."}

    payload = _build_request_payload(checkin)
    try:
        response = requests.post(
            f"{settings.AI_ENGINE_URL.rstrip('/')}{ANALYZE_PATH}",
            json=payload,
            timeout=settings.AI_ENGINE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        return _parse_response(data)
    except (requests.RequestException, ValueError) as exc:
        logger.warning("AI engine call failed for checkin %s: %s", checkin.id, exc)
        return {**UNAVAILABLE_RESULT, "reason": "AI engine call failed."}
