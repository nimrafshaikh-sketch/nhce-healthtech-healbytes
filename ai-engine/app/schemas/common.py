"""Shared base model, enums, and primitive types used by both the AI request
and response contracts.

Enum string values in this module are intentionally the literal wire values
from the agreed backend contract (see `backend/apps/checkins/ai_client.py`
on the `feature/backend` branch) — e.g. `RiskLevel.LOW.value == "low"`, not
`"Low"` — so a model can be serialized straight onto the wire with no
casing/translation step.
"""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class StrictModel(BaseModel):
    """Base model that rejects unexpected fields, for strict contract validation."""

    model_config = ConfigDict(extra="forbid")


NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strict=True)]
"""A string that must be present, non-empty, and not silently coerced from
another type (e.g. a number or boolean)."""


class RiskLevel(str, Enum):
    """Standardized risk classification returned by the AI Engine.

    Values match `ai_client.VALID_RISK_LEVELS` exactly (`{"low", "medium",
    "high"}`) — the backend rejects any other value as unrecognized.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class NotificationRecipient(str, Enum):
    """Who the AI Engine suggests should be notified about this check-in.

    Informational only: per `ai_client.py`'s own docstring, the backend
    still decides who is actually alerted via its own rule engine
    (`apps.alerts.rules`) — this field is stored for reference/logging, not
    acted on directly. Values follow the example set documented in
    `ai_client.py` (`"doctor" | "caretaker" | "both" | "none"`).
    """

    NONE = "none"
    CARETAKER = "caretaker"
    DOCTOR = "doctor"
    BOTH = "both"
