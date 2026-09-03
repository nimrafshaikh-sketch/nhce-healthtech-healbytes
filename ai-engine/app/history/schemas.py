"""Phase 2 patient-history request/response contract.

Deliberately separate from `app/schemas/request.py` / `app/schemas/response.py`
(the Phase 1 `/analyze` contract) - Phase 2 is a different capability with a
different shape, and must not change Phase 1's contract or behavior.

Field names and enum values below are taken directly from the real backend
serializers as audited in the repository (`backend/apps/checkins`,
`backend/apps/medications`, `backend/apps/labtests`,
`backend/apps/appointments`), not invented. Where the backend has no field
(e.g. lab result units or reference ranges), no field is added here either -
that information is simply unavailable.

The AI Engine has no database access, so every record the summary is
computed from must be supplied by the caller in the request body.
"""

from __future__ import annotations

from datetime import date, datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import Field

from app.schemas.common import MedicationAdherenceStatus, NonEmptyStr, StrictModel

# --- Enums mirroring real backend TextChoices (values copied verbatim) -----


class CheckinRiskLevel(str, Enum):
    """Mirrors `backend.apps.checkins.models.DailyCheckin.RiskLevel`."""

    PENDING = "pending"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    UNAVAILABLE = "unavailable"


class MedicationFrequency(str, Enum):
    """Mirrors `backend.apps.medications.models.Medication.Frequency`."""

    ONCE_DAILY = "once_daily"
    TWICE_DAILY = "twice_daily"
    THREE_TIMES_DAILY = "three_times_daily"
    WEEKLY = "weekly"
    AS_NEEDED = "as_needed"


class LabTestName(str, Enum):
    """Mirrors `backend.apps.labtests.models.LabTestRequest.TestName`."""

    CBC = "CBC"
    BLOOD_GLUCOSE = "BLOOD_GLUCOSE"
    LIPID_PROFILE = "LIPID_PROFILE"
    HBA1C = "HBA1C"
    KFT = "KFT"
    LFT = "LFT"
    TFT = "TFT"
    URINALYSIS = "URINALYSIS"


class LabTestPriority(str, Enum):
    """Mirrors `backend.apps.labtests.models.LabTestRequest.Priority`."""

    ROUTINE = "routine"
    URGENT = "urgent"


class LabTestStatus(str, Enum):
    """Mirrors `backend.apps.labtests.models.LabTestRequest.Status`."""

    REQUESTED = "requested"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class AppointmentStatus(str, Enum):
    """Mirrors `backend.apps.appointments.models.Appointment.Status`."""

    SCHEDULED = "scheduled"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class TrendDirection(str, Enum):
    """Directional trend classification. Deliberately neutral (not
    improving/worsening) for vitals, since a rising or falling numeric
    reading is not inherently good or bad without clinical context this
    module does not have."""

    INCREASING = "increasing"
    DECREASING = "decreasing"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


class SymptomTrend(str, Enum):
    """Directional trend in reported-symptom count. 'improving'/'worsening'
    here means fewer/more symptoms reported over time - an engineering
    heuristic for prioritization, not a clinical judgment."""

    IMPROVING = "improving"
    WORSENING = "worsening"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


TREND_DISCLAIMER = (
    "This trend is a deterministic calculation over the supplied structured "
    "history only. It is not a clinical assessment and is not medically validated."
)

# --- Request: supplied history records --------------------------------------


class CheckinRecord(StrictModel):
    """Mirrors `DailyCheckinSerializer` fields relevant to a history summary."""

    id: int
    checkin_date: date
    symptoms: List[NonEmptyStr] = Field(default_factory=list)
    mood: str = ""
    pain_level: Optional[int] = Field(default=None, ge=0, le=10)
    vitals: Dict[str, float] = Field(default_factory=dict)
    ai_risk_level: Optional[CheckinRiskLevel] = None
    ai_risk_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    created_at: Optional[datetime] = None


class MedicationRecord(StrictModel):
    """Mirrors `MedicationSerializer` fields relevant to a history summary."""

    id: int
    name: NonEmptyStr
    dosage: NonEmptyStr
    frequency: MedicationFrequency
    start_date: date
    end_date: Optional[date] = None
    is_active: bool = True


class LabTestRecord(StrictModel):
    """Mirrors `LabTestRequestSerializer` (+ nested result) fields relevant
    to a history summary. No units or reference ranges exist in the real
    backend contract, so none are modeled here.

    `result_date` and `created_at` are deliberately two separate fields
    because the real backend has two separate, non-interchangeable
    timestamps here:
      - `result_date` should be populated from when the result was actually
        recorded (`LabTestResultSerializer.created_at` on the nested
        `result` object) - this is the field the summary prefers.
      - `created_at`, when supplied on a record that has no `result_date`,
        is used ONLY as a fallback and MUST also be the lab RESULT's
        recorded time (the nested `result.created_at`), never the lab
        REQUEST's own `created_at` (i.e. not `LabTestRequestSerializer
        .created_at`, which is when the doctor ordered the test - an
        unrelated, typically much earlier timestamp). Sending the request's
        `created_at` here would make an old, slow-to-result test look more
        recent than a genuinely newer result.

    See `app/history/summary_service.py::_lab_sort_key` for how these two
    fields are prioritized when selecting the latest lab result.
    """

    id: int
    test_name: LabTestName
    priority: LabTestPriority = LabTestPriority.ROUTINE
    status: LabTestStatus
    result_text: Optional[str] = None
    result_date: Optional[datetime] = None
    reviewed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    """Fallback-only timestamp, used solely when `result_date` is absent.
    Must be the lab RESULT's recorded time, not the lab REQUEST's order
    time - see the class docstring above."""


class AppointmentRecord(StrictModel):
    """Mirrors `AppointmentSerializer` fields relevant to a history summary."""

    id: int
    scheduled_at: datetime
    status: AppointmentStatus
    reason: str = ""


class MedicationReminderLogRecord(StrictModel):
    """Mirrors `MedicationReminderLogSerializer` fields
    (`backend.apps.medications.models.MedicationReminderLog`) - one row per
    reminder actually dispatched for a medication, used to deterministically
    derive an adherence signal (see `medication_adherence` on
    `PatientHistory` / `compute_medication_adherence` in
    `summary_service.py`). `sent_at` mirrors the real model's
    `auto_now_add=True` field - a dispatched reminder always has one.
    `acknowledged_at` is `None` until the patient acknowledges it."""

    id: int
    medication_id: int = Field(description="FK to the MedicationRecord.id this reminder belongs to.")
    scheduled_for: datetime
    sent_at: datetime
    acknowledged_at: Optional[datetime] = None


class PatientHistoryRequest(StrictModel):
    """Full Phase 2 request contract. All history lists default to empty -
    a patient with no check-ins, no medications, no lab results, or no
    appointments is a valid, expected input, not an error."""

    patient_id: NonEmptyStr
    request_id: NonEmptyStr
    as_of: Optional[datetime] = Field(
        default=None,
        description="Reference timestamp for 'days since' calculations. "
        "Defaults to the current UTC time if omitted.",
    )

    checkins: List[CheckinRecord] = Field(default_factory=list)
    medications: List[MedicationRecord] = Field(default_factory=list)
    lab_tests: List[LabTestRecord] = Field(default_factory=list)
    appointments: List[AppointmentRecord] = Field(default_factory=list)
    medication_reminder_logs: List[MedicationReminderLogRecord] = Field(
        default_factory=list,
        description="Optional. Reminder-dispatch history used to compute "
        "medication_adherence in the response. Safe to omit entirely - "
        "existing callers of this endpoint are unaffected.",
    )


# --- Response: computed summary ---------------------------------------------


class LatestCheckinSummary(StrictModel):
    id: int
    checkin_date: date
    symptoms: List[str]
    mood: str
    pain_level: Optional[int]
    ai_risk_level: Optional[CheckinRiskLevel]


class SymptomTrendSummary(StrictModel):
    trend: SymptomTrend
    observed_checkins: int
    latest_symptom_count: Optional[int] = None
    previous_symptom_count: Optional[int] = None
    detail: str


class VitalTrendEntry(StrictModel):
    latest_value: float
    previous_value: float
    delta: float
    trend: TrendDirection


class VitalTrendSummary(StrictModel):
    observed_checkins_with_vitals: int
    vitals: Dict[str, VitalTrendEntry] = Field(default_factory=dict)
    detail: str


class MedicationSummary(StrictModel):
    id: int
    name: str
    dosage: str
    frequency: MedicationFrequency
    is_current: bool
    start_date: date
    end_date: Optional[date] = None


class LatestLabSummary(StrictModel):
    id: int
    test_name: LabTestName
    status: LabTestStatus
    result_text: str
    result_date: Optional[datetime] = None
    reviewed: bool


class OpenFollowUpSummary(StrictModel):
    """The soonest still-upcoming appointment with an open status
    (`scheduled` or `confirmed`). See
    `app/history/summary_service.py::compute_open_follow_up` for the exact
    selection rule - in particular, an open-status appointment whose
    `scheduled_at` has already passed relative to the request's `as_of` is
    excluded, not selected, so it can never mask a genuine future one."""

    id: int
    scheduled_at: datetime
    status: AppointmentStatus
    reason: str


MEDICATION_ADHERENCE_DISCLAIMER = (
    "Medication-adherence status here is a deterministic engineering "
    "heuristic computed only from the supplied reminder-dispatch records "
    "(acknowledged vs. sent). It is not a clinically validated "
    "medication-safety judgment, diagnosis, or treatment recommendation, "
    "and a medication with no reminder-log data is always 'unknown', "
    "never penalized."
)


class MedicationAdherenceDetail(StrictModel):
    """Deterministic per-medication adherence classification. See
    `compute_medication_adherence` in `summary_service.py` for the exact
    reminders_acknowledged/reminders_sent thresholds used."""

    medication_id: int
    name: str
    status: MedicationAdherenceStatus
    reminders_sent: int
    reminders_acknowledged: int
    adherence_rate: Optional[float] = Field(
        default=None,
        description="reminders_acknowledged / reminders_sent, 0.0-1.0. "
        "None only when reminders_sent == 0 (status is then 'unknown').",
    )


class MedicationAdherenceSummary(StrictModel):
    """Patient-level medication-adherence rollup. Always present in the
    response (even with zero medications, as an empty/'unknown' summary) -
    see `PatientHistory.medication_adherence`."""

    overall_status: MedicationAdherenceStatus
    medications: List[MedicationAdherenceDetail] = Field(default_factory=list)
    detail: str


class PatientHistory(StrictModel):
    checkin_count: int
    days_since_last_checkin: Optional[int] = None
    latest_checkin: Optional[LatestCheckinSummary] = None
    symptom_trend: SymptomTrendSummary
    vital_trend: VitalTrendSummary
    medications: List[MedicationSummary] = Field(default_factory=list)
    latest_lab: Optional[LatestLabSummary] = None
    open_follow_up: Optional[OpenFollowUpSummary] = None
    """`None` when there is no `scheduled`/`confirmed` appointment still
    ahead of `as_of` - see `OpenFollowUpSummary` docstring."""
    medication_adherence: MedicationAdherenceSummary
    """New, additive field - computed from `medication_reminder_logs` on the
    request (see `MedicationAdherenceSummary`). Always present; existing
    Phase 2 consumers that only read the pre-existing fields are
    unaffected."""


class PatientHistorySummaryResponse(StrictModel):
    patient_id: NonEmptyStr
    request_id: NonEmptyStr
    generated_at: datetime
    history: PatientHistory
