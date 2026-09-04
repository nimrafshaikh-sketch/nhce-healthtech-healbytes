"""AI Engine input contract.

Defines the structured payload the backend must send for a single patient
check-in analysis request. This module only defines and validates the shape
of incoming data — no risk-analysis logic is implemented here.
"""

from datetime import date, datetime
from typing import List, Optional

from pydantic import Field

from app.schemas.common import (
    DurationUnit,
    MedicationAdherenceStatus,
    NonEmptyStr,
    RiskLevel,
    SeverityLevel,
    StrictModel,
)


class Duration(StrictModel):
    """How long the current symptoms have been present."""

    value: int = Field(..., gt=0, strict=True, description="Must be a real int, not a numeric string or bool")
    unit: DurationUnit


class CheckInData(StrictModel):
    """The patient's current, self-reported check-in."""

    symptoms: List[NonEmptyStr] = Field(..., min_length=1, description="Reported symptom names")
    severity: SeverityLevel
    duration: Duration


class MedicationAdherenceRecord(StrictModel):
    """Adherence status for a single prescribed medication."""

    medication_name: NonEmptyStr
    adherence_status: MedicationAdherenceStatus = MedicationAdherenceStatus.UNKNOWN
    last_taken: Optional[date] = None


class MedicalContext(StrictModel):
    """Background medical information relevant to future risk analysis."""

    medical_history: List[NonEmptyStr] = Field(default_factory=list)
    medication_adherence: List[MedicationAdherenceRecord] = Field(default_factory=list)


class PreviousCheckInSummary(StrictModel):
    """A compact record of a prior check-in, used for future trend detection."""

    request_id: NonEmptyStr
    timestamp: datetime
    severity: SeverityLevel
    risk_level: Optional[RiskLevel] = None


class HistoricalContext(StrictModel):
    """Prior check-ins supplied by the backend for trend analysis."""

    previous_checkins: List[PreviousCheckInSummary] = Field(default_factory=list)


class AIAnalysisRequest(StrictModel):
    """Full request contract sent from the backend to the AI Engine."""

    patient_id: NonEmptyStr
    request_id: NonEmptyStr
    timestamp: datetime

    check_in: CheckInData
    medical_context: MedicalContext = Field(default_factory=MedicalContext)
    historical_context: HistoricalContext = Field(default_factory=HistoricalContext)
