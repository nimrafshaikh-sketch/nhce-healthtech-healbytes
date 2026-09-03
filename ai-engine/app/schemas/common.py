"""Shared base model, enums, and primitive types used by both the AI request
and response contracts.
"""

from enum import Enum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class StrictModel(BaseModel):
    """Base model that rejects unexpected fields, for strict contract validation."""

    model_config = ConfigDict(extra="forbid")


NonEmptyStr = Annotated[str, StringConstraints(min_length=1, strict=True)]
"""A string that must be present, non-empty, and not silently coerced from
another type (e.g. a number or boolean). Used for every required or
optional-but-non-blank text field in the contract (IDs, names, free text)."""


class RiskLevel(str, Enum):
    """Standardized risk classification returned by the AI Engine."""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class SeverityLevel(str, Enum):
    """Self-reported severity of a check-in."""

    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class DurationUnit(str, Enum):
    """Unit for how long a symptom/condition has been present."""

    HOURS = "hours"
    DAYS = "days"
    WEEKS = "weeks"


class MedicationAdherenceStatus(str, Enum):
    """Adherence classification for a single medication."""

    ADHERENT = "adherent"
    PARTIALLY_ADHERENT = "partially_adherent"
    NON_ADHERENT = "non_adherent"
    UNKNOWN = "unknown"


class AlertRecipient(str, Enum):
    """Who the AI Engine recommends should be notified about this check-in."""

    NONE = "none"
    CARE_TEAM = "care_team"
    PHYSICIAN = "physician"
    EMERGENCY_SERVICES = "emergency_services"
