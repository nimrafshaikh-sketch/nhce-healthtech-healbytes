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

from app.analysis.lab_reference import assess_lab_result
from app.analysis.response_builder import build_response
from app.analysis.risk_engine import MODEL_VERSION
from app.config import settings
from app.schemas.lab import LabAnalysisRequest, LabAnalysisResponse
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


@router.post("/lab-analysis", response_model=LabAnalysisResponse, tags=["analysis"])
def analyze_lab_result(payload: LabAnalysisRequest) -> LabAnalysisResponse:
    """Deterministically assess a single lab-technician-submitted result
    against known reference ranges (see `app/analysis/lab_reference.py`).
    Same non-ML, non-diagnostic guarantees as `/analyze` - a transparent
    rule-based baseline, not a clinical diagnostic system.
    """

    logger.info(
        "Analyzing lab result %s (%s) for patient %s",
        payload.request_id,
        payload.test_name,
        payload.patient_id,
    )
    try:
        assessment = assess_lab_result(payload.test_name, payload.result_text)
        return LabAnalysisResponse(
            request_id=payload.request_id,
            timestamp=payload.timestamp,
            test_name=payload.test_name,
            numeric_value=assessment["numeric_value"],
            unit=assessment["unit"],
            reference_range=assessment["reference_range"],
            status=assessment["status"],
            risk_level=assessment["risk_level"],
            explanation=assessment["explanation"],
            model_version=MODEL_VERSION,
        )
    except Exception:
        logger.exception("Unexpected error analyzing lab result %s", payload.request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while analyzing the lab result.",
        )
