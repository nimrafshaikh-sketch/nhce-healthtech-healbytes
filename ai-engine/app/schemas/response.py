"""AI Engine output contract.

Defines the structured, validated response returned by the AI Engine. Actual
risk-scoring logic is not implemented in Phase 0 — this module only defines
and validates the shape of outgoing data.
"""

from datetime import datetime
from typing import Optional

from pydantic import Field

from app.schemas.common import AlertRecipient, NonEmptyStr, RiskLevel, StrictModel


class AIAnalysisResponse(StrictModel):
    """Full response contract returned by the AI Engine to the backend.

    Every field below is always present in a serialized response, giving the
    backend a single predictable shape to deserialize. `follow_up_action` and
    `explanation` are allowed to be `null`; every other field is required.
    """

    request_id: NonEmptyStr
    timestamp: datetime

    risk_level: RiskLevel
    risk_score: float = Field(
        ..., ge=0.0, le=100.0, strict=True, description="0-100 scale; higher means more risk"
    )
    reason: NonEmptyStr

    alert_recipient: AlertRecipient
    follow_up_action: Optional[NonEmptyStr] = None
    explanation: Optional[NonEmptyStr] = None

    model_version: NonEmptyStr
