"""Phase 2 deterministic patient-history summary computation.

Every value here is derived by explicit, documented calculation over the
records supplied in the request - counting, sorting, date arithmetic, and
simple monotonic-sequence comparison. Nothing is inferred by an LLM or ML
model, and no field is fabricated: where the supplied data can't support a
value (no check-ins, no lab results with a status of completed, etc.) the
corresponding response field is explicitly `None` / empty, never guessed.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from app.history.schemas import (
    AppointmentRecord,
    AppointmentStatus,
    CheckinRecord,
    LabTestRecord,
    LabTestStatus,
    LatestCheckinSummary,
    LatestLabSummary,
    MedicationAdherenceDetail,
    MedicationAdherenceSummary,
    MEDICATION_ADHERENCE_DISCLAIMER,
    MedicationReminderLogRecord,
    MedicationRecord,
    MedicationSummary,
    OpenFollowUpSummary,
    PatientHistory,
    PatientHistoryRequest,
    PatientHistorySummaryResponse,
    SymptomTrend,
    SymptomTrendSummary,
    TREND_DISCLAIMER,
    TrendDirection,
    VitalTrendEntry,
    VitalTrendSummary,
)
from app.schemas.common import MedicationAdherenceStatus

MIN_CHECKINS_FOR_SYMPTOM_TREND = 2
"""Fewer than this many check-ins is insufficient evidence for a directional
symptom-count trend - mirrors the evidence-gating principle already used by
the Phase 1 historical-trend heuristic (see `app/analysis/trend_detector.py`),
applied independently here to the real check-in fields Phase 2 receives."""

# --- Ordering helpers ---------------------------------------------------------


def _sorted_checkins(checkins: List[CheckinRecord]) -> List[CheckinRecord]:
    """Chronological order (oldest first), tie-broken by id for determinism
    when two check-ins share a date."""

    return sorted(checkins, key=lambda c: (c.checkin_date, c.id))


# --- Check-in count / recency --------------------------------------------------


def compute_checkin_count(checkins: List[CheckinRecord]) -> int:
    return len(checkins)


def latest_checkin_record(checkins: List[CheckinRecord]) -> Optional[CheckinRecord]:
    if not checkins:
        return None
    return _sorted_checkins(checkins)[-1]


def build_latest_checkin_summary(checkins: List[CheckinRecord]) -> Optional[LatestCheckinSummary]:
    latest = latest_checkin_record(checkins)
    if latest is None:
        return None
    return LatestCheckinSummary(
        id=latest.id,
        checkin_date=latest.checkin_date,
        symptoms=list(latest.symptoms),
        mood=latest.mood,
        pain_level=latest.pain_level,
        ai_risk_level=latest.ai_risk_level,
    )


def compute_days_since_last_checkin(
    checkins: List[CheckinRecord], as_of: datetime
) -> Optional[int]:
    latest = latest_checkin_record(checkins)
    if latest is None:
        return None
    return (as_of.date() - latest.checkin_date).days


# --- Symptom trend --------------------------------------------------------------


def compute_symptom_trend(checkins: List[CheckinRecord]) -> SymptomTrendSummary:
    """Compare reported-symptom counts across chronologically ordered
    check-ins. Strictly increasing counts -> 'worsening'; strictly
    decreasing -> 'improving'; anything else (including flat) -> 'stable'.
    Fewer than `MIN_CHECKINS_FOR_SYMPTOM_TREND` check-ins -> 'insufficient_data'.
    """

    observed = len(checkins)
    if observed < MIN_CHECKINS_FOR_SYMPTOM_TREND:
        return SymptomTrendSummary(
            trend=SymptomTrend.INSUFFICIENT_DATA,
            observed_checkins=observed,
            detail=(
                f"Observed {observed} check-in(s); at least "
                f"{MIN_CHECKINS_FOR_SYMPTOM_TREND} are required for a symptom-count "
                f"trend. {TREND_DISCLAIMER}"
            ),
        )

    ordered = _sorted_checkins(checkins)
    counts = [len(c.symptoms) for c in ordered]
    deltas = [later - earlier for earlier, later in zip(counts, counts[1:])]

    if all(delta > 0 for delta in deltas):
        trend = SymptomTrend.WORSENING
    elif all(delta < 0 for delta in deltas):
        trend = SymptomTrend.IMPROVING
    else:
        trend = SymptomTrend.STABLE

    previous_count = counts[-2]
    latest_count = counts[-1]

    return SymptomTrendSummary(
        trend=trend,
        observed_checkins=observed,
        latest_symptom_count=latest_count,
        previous_symptom_count=previous_count,
        detail=(
            f"Reported-symptom count sequence across {observed} check-in(s): "
            f"{counts}. Engineering inference: '{trend.value}'. {TREND_DISCLAIMER}"
        ),
    )


# --- Vital trend ------------------------------------------------------------------


def compute_vital_trend(checkins: List[CheckinRecord]) -> VitalTrendSummary:
    """For each vital key present on the most recent check-in, compare it to
    the same key's most recent prior value (searching backward through
    chronological history). A key with no prior reading is omitted, not
    guessed at."""

    checkins_with_vitals = [c for c in checkins if c.vitals]
    ordered = _sorted_checkins(checkins_with_vitals)

    if len(ordered) < 2:
        return VitalTrendSummary(
            observed_checkins_with_vitals=len(ordered),
            vitals={},
            detail=(
                f"Observed {len(ordered)} check-in(s) with recorded vitals; at "
                f"least 2 are required to compute a per-vital trend. {TREND_DISCLAIMER}"
            ),
        )

    latest = ordered[-1]
    history_before_latest = ordered[:-1]

    entries = {}
    for key, latest_value in latest.vitals.items():
        previous_value = None
        for prior in reversed(history_before_latest):
            if key in prior.vitals:
                previous_value = prior.vitals[key]
                break
        if previous_value is None:
            continue

        delta = latest_value - previous_value
        if delta > 0:
            direction = TrendDirection.INCREASING
        elif delta < 0:
            direction = TrendDirection.DECREASING
        else:
            direction = TrendDirection.STABLE

        entries[key] = VitalTrendEntry(
            latest_value=latest_value,
            previous_value=previous_value,
            delta=delta,
            trend=direction,
        )

    if not entries:
        detail = (
            f"Observed {len(ordered)} check-in(s) with recorded vitals, but no "
            "vital key on the latest check-in has a prior recorded value to "
            f"compare against. {TREND_DISCLAIMER}"
        )
    else:
        detail = (
            f"Compared the latest check-in's vitals against the most recent "
            f"prior reading for each key, across {len(ordered)} check-in(s) with "
            f"recorded vitals. {TREND_DISCLAIMER}"
        )

    return VitalTrendSummary(
        observed_checkins_with_vitals=len(ordered),
        vitals=entries,
        detail=detail,
    )


# --- Medications --------------------------------------------------------------


def _is_current(medication: MedicationRecord, as_of_date) -> bool:
    if not medication.is_active:
        return False
    if medication.start_date > as_of_date:
        return False
    if medication.end_date is not None and medication.end_date < as_of_date:
        return False
    return True


def compute_current_medications(
    medications: List[MedicationRecord], as_of: datetime
) -> List[MedicationSummary]:
    as_of_date = as_of.date()
    current = [m for m in medications if _is_current(m, as_of_date)]
    # Deterministic order: name, then id.
    current.sort(key=lambda m: (m.name, m.id))
    return [
        MedicationSummary(
            id=m.id,
            name=m.name,
            dosage=m.dosage,
            frequency=m.frequency,
            is_current=True,
            start_date=m.start_date,
            end_date=m.end_date,
        )
        for m in current
    ]


# --- Medication adherence -------------------------------------------------------

ADHERENT_RATE_THRESHOLD = 0.8
"""acknowledged/sent ratio at or above this is classified 'adherent'."""

PARTIALLY_ADHERENT_RATE_THRESHOLD = 0.5
"""acknowledged/sent ratio at or above this (but below the adherent
threshold) is classified 'partially_adherent'; below this is
'non_adherent'. Both thresholds are hand-picked engineering defaults for
this hackathon MVP - not medically validated - exactly like every other
bounded threshold in this codebase (see e.g. `risk_engine.py`)."""


def _classify_medication_adherence(sent: int, acknowledged: int) -> MedicationAdherenceStatus:
    """Deterministic per-medication classification from reminder-dispatch
    counts. No reminder-log data at all -> 'unknown', never penalized -
    mirrors the same "missing data is never punished" rule already used by
    `app/analysis/medication_adherence.py` in the Phase 1 pipeline."""

    if sent == 0:
        return MedicationAdherenceStatus.UNKNOWN
    rate = acknowledged / sent
    if rate >= ADHERENT_RATE_THRESHOLD:
        return MedicationAdherenceStatus.ADHERENT
    if rate >= PARTIALLY_ADHERENT_RATE_THRESHOLD:
        return MedicationAdherenceStatus.PARTIALLY_ADHERENT
    return MedicationAdherenceStatus.NON_ADHERENT


_OVERALL_STATUS_PRIORITY = [
    MedicationAdherenceStatus.NON_ADHERENT,
    MedicationAdherenceStatus.PARTIALLY_ADHERENT,
    MedicationAdherenceStatus.ADHERENT,
]
"""Worst-first priority for rolling up per-medication statuses into one
overall status: any non_adherent medication makes the overall picture
non_adherent regardless of how many others are fine, then
partially_adherent, then adherent; 'unknown' is the fallback when nothing
more concerning was observed."""


def compute_medication_adherence(
    medications: List[MedicationRecord],
    reminder_logs: List[MedicationReminderLogRecord],
) -> MedicationAdherenceSummary:
    """Deterministically compute a per-medication and overall adherence
    classification from supplied reminder-dispatch records - the AI Engine's
    first real medication-adherence *computation* (Phase 1's
    `medication_adherence.py` only consumes an already-known
    `adherence_status`; nothing before this produced one from data).

    Every medication supplied is evaluated (not just currently-active ones),
    since a just-ended medication's adherence history is still relevant
    context. A medication with zero matching reminder logs is 'unknown',
    never penalized.
    """

    if not medications:
        return MedicationAdherenceSummary(
            overall_status=MedicationAdherenceStatus.UNKNOWN,
            medications=[],
            detail=f"No medications supplied. {MEDICATION_ADHERENCE_DISCLAIMER}",
        )

    logs_by_medication: dict[int, List[MedicationReminderLogRecord]] = {}
    for log in reminder_logs:
        logs_by_medication.setdefault(log.medication_id, []).append(log)

    details = []
    for medication in sorted(medications, key=lambda m: (m.name, m.id)):
        logs = logs_by_medication.get(medication.id, [])
        sent = len(logs)
        acknowledged = sum(1 for log in logs if log.acknowledged_at is not None)
        status = _classify_medication_adherence(sent, acknowledged)
        rate = (acknowledged / sent) if sent > 0 else None
        details.append(
            MedicationAdherenceDetail(
                medication_id=medication.id,
                name=medication.name,
                status=status,
                reminders_sent=sent,
                reminders_acknowledged=acknowledged,
                adherence_rate=rate,
            )
        )

    statuses = {d.status for d in details}
    overall_status = next(
        (status for status in _OVERALL_STATUS_PRIORITY if status in statuses),
        MedicationAdherenceStatus.UNKNOWN,
    )

    evaluated = sum(1 for d in details if d.reminders_sent > 0)
    detail = (
        f"Evaluated {len(details)} medication(s), {evaluated} with reminder-dispatch "
        f"data. Engineering inference: overall adherence classified as "
        f"'{overall_status.value}' (worst-observed-status rollup). {MEDICATION_ADHERENCE_DISCLAIMER}"
    )

    return MedicationAdherenceSummary(
        overall_status=overall_status,
        medications=details,
        detail=detail,
    )


# --- Latest lab result --------------------------------------------------------

_MIN_DATETIME = datetime.min.replace(tzinfo=timezone.utc)
"""Sentinel used only when a lab record has neither `result_date` nor
`created_at` - so such a record still sorts deterministically (last), never
raising a naive/aware datetime comparison error."""


def _lab_sort_key(lab: LabTestRecord):
    """Two-tier, most-recent-first key:

    Tier 1 (highest priority): any lab with a real `result_date` - ranked
    among themselves by that `result_date`. A record with a real
    `result_date` always outranks one without, regardless of how recent the
    other's `created_at` fallback is.

    Tier 2 (fallback only): labs with no `result_date` at all - ranked among
    themselves by `created_at` (see `LabTestRecord.created_at` docstring:
    this must be the *result's* recorded time, not the request's order
    time). A record with neither field sorts last within this tier.

    `lab.id` breaks ties for full determinism.
    """

    has_result_date = lab.result_date is not None
    if has_result_date:
        reference = lab.result_date
    else:
        reference = lab.created_at or _MIN_DATETIME
    return (has_result_date, reference, lab.id)


def compute_latest_lab(lab_tests: List[LabTestRecord]) -> Optional[LatestLabSummary]:
    completed_with_result = [
        lab
        for lab in lab_tests
        if lab.status == LabTestStatus.COMPLETED and lab.result_text
    ]
    if not completed_with_result:
        return None

    latest = max(completed_with_result, key=_lab_sort_key)
    return LatestLabSummary(
        id=latest.id,
        test_name=latest.test_name,
        status=latest.status,
        result_text=latest.result_text,
        result_date=latest.result_date,
        reviewed=latest.reviewed_at is not None,
    )


# --- Open follow-up / appointment ---------------------------------------------

_OPEN_APPOINTMENT_STATUSES = {AppointmentStatus.SCHEDULED, AppointmentStatus.CONFIRMED}


def compute_open_follow_up(
    appointments: List[AppointmentRecord], as_of: datetime
) -> Optional[OpenFollowUpSummary]:
    """The soonest *upcoming* appointment in an open state (`scheduled` or
    `confirmed`).

    Both conditions are required:
      - status is `scheduled` or `confirmed` (`completed`, `cancelled`, and
        `no_show` are never returned, regardless of date);
      - `scheduled_at` is not before `as_of` (an open-status appointment
        whose date has already passed is stale, not upcoming, and must not
        mask a genuine future appointment - it is simply excluded here).

    Returns `None` when there is no open appointment still ahead of `as_of`.
    """

    upcoming_open = [
        a
        for a in appointments
        if a.status in _OPEN_APPOINTMENT_STATUSES and a.scheduled_at >= as_of
    ]
    if not upcoming_open:
        return None

    soonest = min(upcoming_open, key=lambda a: (a.scheduled_at, a.id))
    return OpenFollowUpSummary(
        id=soonest.id,
        scheduled_at=soonest.scheduled_at,
        status=soonest.status,
        reason=soonest.reason,
    )


# --- Top-level orchestration ---------------------------------------------------


def build_history_summary(request: PatientHistoryRequest) -> PatientHistorySummaryResponse:
    """Compose the full Phase 2 response from a validated request. Pure
    function: no I/O, no randomness, no clock reads beyond the supplied or
    defaulted `as_of`."""

    as_of = request.as_of or datetime.now(timezone.utc)

    history = PatientHistory(
        checkin_count=compute_checkin_count(request.checkins),
        days_since_last_checkin=compute_days_since_last_checkin(request.checkins, as_of),
        latest_checkin=build_latest_checkin_summary(request.checkins),
        symptom_trend=compute_symptom_trend(request.checkins),
        vital_trend=compute_vital_trend(request.checkins),
        medications=compute_current_medications(request.medications, as_of),
        latest_lab=compute_latest_lab(request.lab_tests),
        open_follow_up=compute_open_follow_up(request.appointments, as_of),
        medication_adherence=compute_medication_adherence(
            request.medications, request.medication_reminder_logs
        ),
    )

    return PatientHistorySummaryResponse(
        patient_id=request.patient_id,
        request_id=request.request_id,
        generated_at=datetime.now(timezone.utc),
        history=history,
    )
