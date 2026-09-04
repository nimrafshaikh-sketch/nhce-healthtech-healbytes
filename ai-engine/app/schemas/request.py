"""AI Engine input contract.

Mirrors, field for field, the payload `backend/apps/checkins/ai_client.py`
(`feature/backend` branch) actually sends:

    {"checkin_id": int, "patient_id": int, "symptoms": [...],
     "pain_level": int|null, "mood": str, "vitals": {...}, "notes": str}

This is a deliberate departure from the richer `check_in`/`medical_context`/
`historical_context` shape this service used before Phase 6 — see
`README.md` for why, and for the fields (`mood`, `vitals`, `notes`) that are
accepted here but not yet used as risk-scoring signals.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import Field, model_validator

from app.schemas.common import NonEmptyStr, StrictModel

PAIN_LEVEL_MIN = 0
PAIN_LEVEL_MAX = 10
"""Assumed standard 0-10 self-reported pain scale. `ai_client.py` does not
document a valid range for `pain_level` — this is a documented assumption,
not a confirmed contract detail. Flag with the backend/product owner before
relying on it; see the Phase 6 section of `README.md`."""


class AIAnalysisRequest(StrictModel):
    """Full request contract sent from the backend to the AI Engine.

    `symptoms` may be empty and `pain_level` may be `null` individually
    (either can genuinely be absent from a real check-in), but at least one
    of the two must carry a usable signal — see `_require_usable_signal`.
    Without that, this deterministic engine has nothing to score and must
    not fabricate a result (see Pydantic validation error -> HTTP 422,
    which `ai_client.py` already treats as a safe "unavailable" outcome).
    """

    checkin_id: int = Field(..., strict=True)
    patient_id: int = Field(..., strict=True)

    symptoms: List[NonEmptyStr] = Field(default_factory=list, description="Reported symptom names")
    pain_level: Optional[int] = Field(
        default=None,
        strict=True,
        ge=PAIN_LEVEL_MIN,
        le=PAIN_LEVEL_MAX,
        description="Self-reported pain scale, assumed 0-10; null if not reported",
    )
    mood: Optional[str] = Field(
        default=None,
        description="Free-text/choice mood field; accepted, not yet scored. Django's "
        "`CharField(blank=True)` sends an unset mood as \"\" (not null) — both are "
        "treated as unspecified, not as a fabricated clinical value.",
    )
    vitals: Dict[str, Any] = Field(
        default_factory=dict,
        description="Free-form vitals payload; shape is not defined by the agreed "
        "contract, so it is accepted as-is and not yet scored",
    )
    notes: Optional[str] = Field(
        default=None, description="Free-text notes; accepted, not analyzed (no NLP/LLM in this phase)"
    )

    @model_validator(mode="after")
    def _require_usable_signal(self) -> "AIAnalysisRequest":
        """Reject requests with neither symptoms nor a pain level.

        This is the "insufficient data" safeguard: rather than fabricating
        a risk score from an empty check-in, the request itself is rejected
        (422), which `ai_client.py` already maps to a safe unavailable
        result on the backend side.
        """

        if not self.symptoms and self.pain_level is None:
            raise ValueError(
                "At least one of `symptoms` (non-empty) or `pain_level` (non-null) "
                "is required to run an analysis."
            )
        return self
