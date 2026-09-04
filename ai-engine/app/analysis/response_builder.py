"""Builds the stable `AIAnalysisResponse` contract from a risk assessment.

This is the seam between the fixed external contract (`app/schemas/response.py`)
and whatever internally produces a `RiskAssessment`. Phase 1 introduced this
seam with `risk_engine.assess`; Phase 2, Phase 3, Phase 4, and Phase 5 extended
the pipeline (baseline + bounded historical-trend + bounded
medication-adherence adjustments + deterministic follow-up recommendation +
controlled AI explanation layer) without any change to `app/api/routes.py`
or core contract integrity — demonstrating exactly the kind of swap a future
ML model could also make later.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.analysis.explanation_service import generate_explanation
from app.analysis.follow_up_recommender import recommend_follow_up
from app.analysis.risk_assessor import assess_with_trend
from app.analysis.risk_engine import MODEL_VERSION
from app.schemas.request import AIAnalysisRequest
from app.schemas.response import AIAnalysisResponse


def build_response(request: AIAnalysisRequest) -> AIAnalysisResponse:
    """Run risk analysis on a validated request and return the response contract.

    Phase 4 populates `follow_up_action` using `recommend_follow_up` based
    on the final computed `risk_level`. Phase 5 populates `explanation`
    using `generate_explanation` downstream from the final assessment.
    """

    assessment = assess_with_trend(request)
    follow_up_action = recommend_follow_up(assessment.risk_level)
    explanation = generate_explanation(assessment, follow_up_action)

    return AIAnalysisResponse(
        request_id=request.request_id,
        timestamp=datetime.now(timezone.utc),
        risk_level=assessment.risk_level,
        risk_score=float(assessment.risk_score),
        reason=assessment.reason,
        alert_recipient=assessment.alert_recipient,
        follow_up_action=follow_up_action,
        explanation=explanation,
        model_version=MODEL_VERSION,
    )
