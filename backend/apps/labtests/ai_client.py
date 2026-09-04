"""Client for the separate AI Engine service - lab-result analysis.

Integration contract (matches the AI Engine's fixed schema - see
ai-engine/app/schemas/lab.py):

    POST {AI_ENGINE_URL}/api/v1/lab-analysis
    Request body (LabAnalysisRequest):
        {
            "patient_id": str,
            "request_id": str,
            "timestamp": ISO datetime,
            "test_name": str,   # one of apps.labtests.models.LabTestRequest.TestName
            "result_text": str,
        }
    Response body (LabAnalysisResponse):
        {
            "request_id": str,
            "timestamp": ISO datetime,
            "test_name": str,
            "numeric_value": float|null,
            "unit": str|null,
            "reference_range": str|null,
            "status": "NORMAL"|"ELEVATED"|"LOW"|"UNKNOWN",
            "risk_level": "Low"|"Medium"|"High",
            "explanation": str,
            "model_version": str,
        }

Follows the exact same fail-open-on-unavailable philosophy as
apps.checkins.ai_client: if AI_ENGINE_URL is unset, the call fails, or the
response is malformed, this returns an "unavailable" result and the lab
result still saves normally - the AI insight is additive, never a blocker
on recording a lab result.
"""
import logging
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

VALID_STATUSES = {"NORMAL", "ELEVATED", "LOW", "UNKNOWN"}
VALID_RISK_LEVELS = {"Low", "Medium", "High"}

LAB_ANALYSIS_PATH = "/api/v1/lab-analysis"

UNAVAILABLE_RESULT = {
    "status": "",
    "risk_level": "unavailable",
    "numeric_value": None,
    "unit": "",
    "reference_range": "",
    "explanation": "",
}


def _parse_response(data: dict) -> dict:
    lab_status = data.get("status")
    if lab_status not in VALID_STATUSES:
        return {**UNAVAILABLE_RESULT, "explanation": "AI engine returned an unrecognized status."}

    risk_level = data.get("risk_level")
    if risk_level not in VALID_RISK_LEVELS:
        return {**UNAVAILABLE_RESULT, "explanation": "AI engine returned an unrecognized risk_level."}

    numeric_value = data.get("numeric_value")
    if isinstance(numeric_value, bool) or not isinstance(numeric_value, (int, float)):
        numeric_value = None

    return {
        "status": lab_status,
        "risk_level": risk_level.lower(),
        "numeric_value": numeric_value,
        "unit": data.get("unit") or "",
        "reference_range": data.get("reference_range") or "",
        "explanation": data.get("explanation") or "",
    }


def analyze_lab_result(result) -> dict:
    """result is a LabTestResult instance (with `request` already resolvable).
    Returns a normalized internal dict:
    {"status": "NORMAL"|"ELEVATED"|"LOW"|"UNKNOWN"|"",
     "risk_level": "low"|"medium"|"high"|"unavailable",
     "numeric_value": float|None, "unit": str, "reference_range": str, "explanation": str}
    """
    if not settings.AI_ENGINE_URL:
        logger.info("AI_ENGINE_URL not configured; skipping AI analysis for lab result %s", result.id)
        return {**UNAVAILABLE_RESULT, "explanation": "AI engine not configured."}

    lab_request = result.request
    payload = {
        "patient_id": str(lab_request.patient_id),
        "request_id": str(result.id),
        "timestamp": timezone.now().isoformat(),
        "test_name": lab_request.test_name,
        "result_text": result.result_text,
    }
    try:
        response = requests.post(
            f"{settings.AI_ENGINE_URL.rstrip('/')}{LAB_ANALYSIS_PATH}",
            json=payload,
            timeout=settings.AI_ENGINE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
        return _parse_response(data)
    except (requests.RequestException, ValueError) as exc:
        logger.warning("AI engine lab-analysis call failed for result %s: %s", result.id, exc)
        return {**UNAVAILABLE_RESULT, "explanation": "AI engine call failed."}
