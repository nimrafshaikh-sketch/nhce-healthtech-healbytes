"""AI Engine output contract.

Field names are literally `riskLevel` / `riskScore` / `reason` /
`recommendedAction` / `notificationRecipient` (not `snake_case` translated
via alias) so the JSON on the wire matches
`backend/apps/checkins/ai_client.py`'s `_parse_response` exactly, with no
alias/serialization step that could silently drift from the agreed
contract. `extra="forbid"` (via `StrictModel`) keeps the response to
exactly these five fields.
"""

from pydantic import Field

from app.schemas.common import NonEmptyStr, NotificationRecipient, RiskLevel, StrictModel


class AIAnalysisResponse(StrictModel):
    """Full response contract returned by the AI Engine to the backend.

    Matches the docstring in `ai_client.py`:

        {
            "riskLevel": "low" | "medium" | "high",
            "riskScore": float,              # 0.0-1.0
            "reason": str,
            "recommendedAction": str,
            "notificationRecipient": str      # informational only
        }
    """

    riskLevel: RiskLevel
    riskScore: float = Field(
        ..., ge=0.0, le=1.0, strict=True, description="0.0-1.0 scale; higher means more risk"
    )
    reason: NonEmptyStr
    recommendedAction: NonEmptyStr
    notificationRecipient: NotificationRecipient
