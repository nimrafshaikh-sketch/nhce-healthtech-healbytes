"""API routes for the AI Engine.

Phase 6 wired `/analyze/` to the exact route and payload shape
`backend/apps/checkins/ai_client.py` (`feature/backend` branch) actually
calls: `POST {AI_ENGINE_URL}/analyze/` (trailing slash, no version prefix —
`ai_client.py` builds the URL as `f"{settings.AI_ENGINE_URL.rstrip('/')}/analyze/"`).
No ML, LLM, external API, database, or real alert/notification delivery is
performed here or anywhere else in this pipeline.
"""

import logging

from fastapi import APIRouter, HTTPException, status

from app.analysis.response_builder import build_response
from app.config import settings
from app.schemas.request import AIAnalysisRequest
from app.schemas.response import AIAnalysisResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", tags=["system"])
def health_check() -> dict:
    """Basic liveness check. Not part of the agreed backend contract — an
    operational convenience only."""

    return {"status": "ok", "service": settings.app_name}


@router.post("/analyze/", response_model=AIAnalysisResponse, tags=["analysis"])
def analyze_checkin(payload: AIAnalysisRequest) -> AIAnalysisResponse:
    """Validate a check-in and return a deterministic rule-based risk assessment.

    The request contract is fully validated by Pydantic before this function
    runs — including the "at least one usable signal" rule in
    `AIAnalysisRequest`, so a request with neither symptoms nor a pain level
    is rejected with 422 rather than producing a fabricated risk score.
    Analysis itself is a deterministic rule engine (see
    `app/analysis/risk_engine.py`); it is a hackathon/MVP baseline, not a
    clinical diagnostic system.
    """

    logger.info(
        "Analyzing checkin %s for patient %s",
        payload.checkin_id,
        payload.patient_id,
    )
    try:
        return build_response(payload)
    except Exception:
        logger.exception("Unexpected error analyzing checkin %s", payload.checkin_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while analyzing the check-in.",
        )
