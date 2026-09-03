"""API routes for the AI Engine.

Phase 0 established the request/response contract. `/analyze` runs the
composed deterministic rule pipeline: a current-check-in baseline (Phase 1,
`app/analysis/risk_engine.py`), a bounded historical-trend adjustment
(Phase 2, `app/analysis/trend_detector.py`), and a bounded
medication-adherence adjustment (Phase 3,
`app/analysis/medication_adherence.py`) — composed in
`app/analysis/risk_assessor.py`, with deterministic follow-up
recommendation (Phase 4, `app/analysis/follow_up_recommender.py`) and
controlled AI explanation (Phase 5, `app/analysis/explanation_service.py`)
applied by `app/analysis/response_builder.py`. No ML, LLM, external API,
database, or real alert/notification delivery is performed here or
anywhere else in this pipeline.
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
    """Basic liveness check."""

    return {"status": "ok", "service": settings.app_name}


@router.post("/analyze", response_model=AIAnalysisResponse, tags=["analysis"])
def analyze_checkin(payload: AIAnalysisRequest) -> AIAnalysisResponse:
    """Validate a check-in and return a Phase 1 rule-based risk assessment.

    The request contract is fully validated by Pydantic before this function
    runs. Analysis itself is a deterministic rule engine (see
    `app/analysis/risk_engine.py`); it is a hackathon/MVP baseline, not a
    clinical diagnostic system.
    """

    logger.info(
        "Analyzing request %s for patient %s",
        payload.request_id,
        payload.patient_id,
    )
    try:
        return build_response(payload)
    except Exception:
        logger.exception("Unexpected error analyzing request %s", payload.request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while analyzing the check-in.",
        )
