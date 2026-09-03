"""Builds the stable `AIAnalysisResponse` contract from a risk assessment.

This is the seam between the fixed external wire contract
(`app/schemas/response.py`) and whatever internally produces a
`RiskAssessment` (currently `app/analysis/risk_engine.py`) — the same kind
of swap a future ML model could make later without touching
`app/api/routes.py` or the contract.

`recommendedAction` is the deterministic `follow_up_recommender` text.
There is no LLM in this pipeline: the wire contract has no `explanation`
field, and even if one is reintroduced later, an LLM must never compute
`riskScore` (see `app/analysis/explanation_service.py`'s architectural
principles, which still apply if it's reattached).
"""

from __future__ import annotations

from app.analysis.follow_up_recommender import recommend_follow_up
from app.analysis.risk_engine import assess
from app.schemas.request import AIAnalysisRequest
from app.schemas.response import AIAnalysisResponse


def build_response(request: AIAnalysisRequest) -> AIAnalysisResponse:
    """Run risk analysis on a validated request and return the response contract."""

    assessment = assess(request)
    recommended_action = recommend_follow_up(assessment.risk_level)

    return AIAnalysisResponse(
        riskLevel=assessment.risk_level,
        riskScore=round(assessment.risk_score / 100.0, 4),
        reason=assessment.reason,
        recommendedAction=recommended_action,
        notificationRecipient=assessment.notification_recipient,
    )
