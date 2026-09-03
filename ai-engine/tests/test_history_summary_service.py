"""Unit tests for the Phase 2 deterministic history-summary calculations."""

from datetime import datetime, timezone

from app.history.schemas import (
    AppointmentRecord,
    CheckinRecord,
    LabTestRecord,
    MedicationReminderLogRecord,
    MedicationRecord,
    PatientHistoryRequest,
    SymptomTrend,
    TrendDirection,
)
from app.history.summary_service import build_history_summary
from app.schemas.common import MedicationAdherenceStatus

AS_OF = datetime(2026, 9, 4, tzinfo=timezone.utc)


def _checkin(id, checkin_date, symptoms, pain_level=None, vitals=None, **kwargs):
    return CheckinRecord(
        id=id,
        checkin_date=checkin_date,
        symptoms=symptoms,
        pain_level=pain_level,
        vitals=vitals or {},
        **kwargs,
    )


def _request(**overrides) -> PatientHistoryRequest:
    base = dict(
        patient_id="1",
        request_id="req-1",
        as_of=AS_OF,
        checkins=[],
        medications=[],
        lab_tests=[],
        appointments=[],
    )
    base.update(overrides)
    return PatientHistoryRequest(**base)


# --- Normal history / basic counts -------------------------------------------


def test_patient_with_normal_history_produces_full_summary():
    request = _request(
        checkins=[
            _checkin(1, "2026-09-01", ["headache"], pain_level=3),
            _checkin(2, "2026-09-03", ["headache", "fatigue"], pain_level=5),
        ],
        medications=[
            MedicationRecord(
                id=10, name="Lisinopril", dosage="10mg", frequency="once_daily",
                start_date="2026-08-01", end_date=None, is_active=True,
            )
        ],
        lab_tests=[
            LabTestRecord(
                id=20, test_name="CBC", priority="routine", status="completed",
                result_text="Normal", result_date="2026-09-02T09:00:00+00:00",
            )
        ],
        appointments=[
            AppointmentRecord(
                id=30, scheduled_at="2026-09-10T10:00:00+00:00", status="scheduled", reason="Follow-up",
            )
        ],
    )

    summary = build_history_summary(request).history

    assert summary.checkin_count == 2
    assert summary.latest_checkin.id == 2
    assert len(summary.medications) == 1
    assert summary.latest_lab.id == 20
    assert summary.open_follow_up.id == 30


def test_no_checkin_history():
    summary = build_history_summary(_request()).history

    assert summary.checkin_count == 0
    assert summary.days_since_last_checkin is None
    assert summary.latest_checkin is None
    assert summary.symptom_trend.trend.value == "insufficient_data"


def test_no_medications():
    request = _request(checkins=[_checkin(1, "2026-09-01", ["cough"])])
    summary = build_history_summary(request).history
    assert summary.medications == []


def test_no_lab_results():
    request = _request(checkins=[_checkin(1, "2026-09-01", ["cough"])])
    summary = build_history_summary(request).history
    assert summary.latest_lab is None


def test_no_open_follow_up():
    request = _request(
        appointments=[
            AppointmentRecord(id=1, scheduled_at="2026-09-01T10:00:00+00:00", status="completed", reason=""),
            AppointmentRecord(id=2, scheduled_at="2026-09-02T10:00:00+00:00", status="cancelled", reason=""),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.open_follow_up is None


# --- Symptom trend -------------------------------------------------------------


def test_insufficient_data_for_trend_calculation_with_single_checkin():
    request = _request(checkins=[_checkin(1, "2026-09-01", ["cough"])])
    summary = build_history_summary(request).history
    assert summary.symptom_trend.trend == SymptomTrend.INSUFFICIENT_DATA
    assert summary.symptom_trend.observed_checkins == 1


def test_improving_symptom_trend():
    request = _request(
        checkins=[
            _checkin(1, "2026-09-01", ["headache", "fatigue", "nausea"]),
            _checkin(2, "2026-09-02", ["headache", "fatigue"]),
            _checkin(3, "2026-09-03", ["headache"]),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.symptom_trend.trend == SymptomTrend.IMPROVING
    assert summary.symptom_trend.latest_symptom_count == 1
    assert summary.symptom_trend.previous_symptom_count == 2


def test_worsening_symptom_trend():
    request = _request(
        checkins=[
            _checkin(1, "2026-09-01", ["headache"]),
            _checkin(2, "2026-09-02", ["headache", "fatigue"]),
            _checkin(3, "2026-09-03", ["headache", "fatigue", "nausea"]),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.symptom_trend.trend == SymptomTrend.WORSENING


def test_stable_symptom_trend():
    request = _request(
        checkins=[
            _checkin(1, "2026-09-01", ["headache"]),
            _checkin(2, "2026-09-02", ["headache", "fatigue"]),
            _checkin(3, "2026-09-03", ["headache"]),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.symptom_trend.trend == SymptomTrend.STABLE


# --- Vital trend -----------------------------------------------------------------


def test_vital_trend_insufficient_data_with_one_vitals_checkin():
    request = _request(checkins=[_checkin(1, "2026-09-01", ["cough"], vitals={"heart_rate": 70})])
    summary = build_history_summary(request).history
    assert summary.vital_trend.vitals == {}
    assert summary.vital_trend.observed_checkins_with_vitals == 1


def test_vital_trend_increasing_and_decreasing_per_key():
    request = _request(
        checkins=[
            _checkin(1, "2026-09-01", ["cough"], vitals={"heart_rate": 70, "temperature_c": 38.0}),
            _checkin(2, "2026-09-02", ["cough"], vitals={"heart_rate": 80, "temperature_c": 37.0}),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.vital_trend.vitals["heart_rate"].trend == TrendDirection.INCREASING
    assert summary.vital_trend.vitals["heart_rate"].delta == 10
    assert summary.vital_trend.vitals["temperature_c"].trend == TrendDirection.DECREASING


def test_vital_trend_skips_key_with_no_prior_reading():
    request = _request(
        checkins=[
            _checkin(1, "2026-09-01", ["cough"], vitals={"heart_rate": 70}),
            _checkin(2, "2026-09-02", ["cough"], vitals={"heart_rate": 72, "temperature_c": 37.5}),
        ]
    )
    summary = build_history_summary(request).history
    assert "temperature_c" not in summary.vital_trend.vitals
    assert "heart_rate" in summary.vital_trend.vitals


# --- Days since last check-in ---------------------------------------------------


def test_days_since_last_checkin():
    request = _request(checkins=[_checkin(1, "2026-09-01", ["cough"])])
    summary = build_history_summary(request).history
    assert summary.days_since_last_checkin == 3  # AS_OF is 2026-09-04


def test_days_since_last_checkin_picks_most_recent_of_several():
    request = _request(
        checkins=[
            _checkin(1, "2026-08-20", ["cough"]),
            _checkin(2, "2026-09-02", ["cough"]),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.days_since_last_checkin == 2


# --- Current medications ---------------------------------------------------------


def test_medication_filtering_active_expired_and_future():
    request = _request(
        medications=[
            MedicationRecord(  # currently active, ongoing
                id=1, name="A", dosage="1", frequency="once_daily",
                start_date="2026-08-01", end_date=None, is_active=True,
            ),
            MedicationRecord(  # expired before as_of
                id=2, name="B", dosage="1", frequency="once_daily",
                start_date="2026-01-01", end_date="2026-02-01", is_active=True,
            ),
            MedicationRecord(  # starts after as_of
                id=3, name="C", dosage="1", frequency="once_daily",
                start_date="2026-12-01", end_date=None, is_active=True,
            ),
            MedicationRecord(  # flagged inactive despite date range covering as_of
                id=4, name="D", dosage="1", frequency="once_daily",
                start_date="2026-08-01", end_date=None, is_active=False,
            ),
        ]
    )
    summary = build_history_summary(request).history
    assert [m.id for m in summary.medications] == [1]


# --- Latest lab selection ----------------------------------------------------------


def test_latest_lab_selection_by_result_date():
    request = _request(
        lab_tests=[
            LabTestRecord(
                id=1, test_name="CBC", status="completed", result_text="old",
                result_date="2026-08-01T00:00:00+00:00",
            ),
            LabTestRecord(
                id=2, test_name="HBA1C", status="completed", result_text="new",
                result_date="2026-09-01T00:00:00+00:00",
            ),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.latest_lab.id == 2
    assert summary.latest_lab.result_text == "new"


def test_latest_lab_ignores_pending_and_resultless_requests():
    request = _request(
        lab_tests=[
            LabTestRecord(id=1, test_name="CBC", status="requested", result_text=None),
            LabTestRecord(id=2, test_name="KFT", status="in_progress", result_text=None),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.latest_lab is None


def test_latest_lab_prefers_result_date_over_a_later_created_at_fallback():
    """Regression test: a completed lab with only a `created_at` fallback
    must NOT outrank a completed lab with a real `result_date`, even if
    that fallback `created_at` is chronologically later than the other
    record's `result_date`."""

    request = _request(
        lab_tests=[
            LabTestRecord(
                id=1, test_name="CBC", status="completed", result_text="has a real result_date",
                result_date="2026-09-03T09:00:00+00:00",
            ),
            LabTestRecord(
                id=2, test_name="URINALYSIS", status="completed",
                result_text="only has created_at, and it's later in raw value",
                result_date=None, created_at="2026-09-03T23:00:00+00:00",
            ),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.latest_lab.id == 1
    assert summary.latest_lab.result_text == "has a real result_date"


def test_latest_lab_falls_back_to_created_at_when_no_lab_has_result_date():
    request = _request(
        lab_tests=[
            LabTestRecord(
                id=1, test_name="CBC", status="completed", result_text="older",
                result_date=None, created_at="2026-08-01T00:00:00+00:00",
            ),
            LabTestRecord(
                id=2, test_name="HBA1C", status="completed", result_text="newer",
                result_date=None, created_at="2026-09-01T00:00:00+00:00",
            ),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.latest_lab.id == 2
    assert summary.latest_lab.result_text == "newer"


# --- Open follow-up / appointment selection -----------------------------------------


def test_open_follow_up_past_and_future_open_picks_future():
    request = _request(
        appointments=[
            AppointmentRecord(id=1, scheduled_at="2026-08-01T10:00:00+00:00", status="scheduled", reason="stale"),
            AppointmentRecord(id=2, scheduled_at="2026-09-15T10:00:00+00:00", status="scheduled", reason="upcoming"),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.open_follow_up.id == 2


def test_open_follow_up_past_scheduled_only_returns_none():
    request = _request(
        appointments=[
            AppointmentRecord(id=1, scheduled_at="2026-08-01T10:00:00+00:00", status="scheduled", reason="stale"),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.open_follow_up is None


def test_open_follow_up_future_confirmed_is_selected():
    request = _request(
        appointments=[
            AppointmentRecord(id=1, scheduled_at="2026-09-15T10:00:00+00:00", status="confirmed", reason="checkup"),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.open_follow_up.id == 1


def test_open_follow_up_ignores_completed_cancelled_and_no_show():
    request = _request(
        appointments=[
            AppointmentRecord(id=1, scheduled_at="2026-09-15T10:00:00+00:00", status="completed", reason=""),
            AppointmentRecord(id=2, scheduled_at="2026-09-16T10:00:00+00:00", status="cancelled", reason=""),
            AppointmentRecord(id=3, scheduled_at="2026-09-17T10:00:00+00:00", status="no_show", reason=""),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.open_follow_up is None


def test_open_follow_up_multiple_future_open_picks_soonest():
    request = _request(
        appointments=[
            AppointmentRecord(id=1, scheduled_at="2026-09-20T10:00:00+00:00", status="confirmed", reason=""),
            AppointmentRecord(id=2, scheduled_at="2026-09-10T10:00:00+00:00", status="scheduled", reason=""),
            AppointmentRecord(id=3, scheduled_at="2026-09-05T10:00:00+00:00", status="completed", reason=""),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.open_follow_up.id == 2


def test_open_follow_up_appointment_exactly_at_as_of_counts_as_upcoming():
    request = _request(
        appointments=[
            AppointmentRecord(id=1, scheduled_at=AS_OF, status="scheduled", reason="exactly now"),
        ]
    )
    summary = build_history_summary(request).history
    assert summary.open_follow_up.id == 1


# --- Medication adherence (computed from reminder-dispatch logs) ---------------------


def _reminder(id, medication_id, acknowledged=True):
    return MedicationReminderLogRecord(
        id=id,
        medication_id=medication_id,
        scheduled_for="2026-09-01T08:00:00+00:00",
        sent_at="2026-09-01T08:00:05+00:00",
        acknowledged_at="2026-09-01T08:10:00+00:00" if acknowledged else None,
    )


def _medication(id, name="Med"):
    return MedicationRecord(
        id=id, name=name, dosage="10mg", frequency="once_daily", start_date="2026-01-01",
    )


def test_medication_adherence_no_medications_supplied():
    summary = build_history_summary(_request()).history.medication_adherence
    assert summary.overall_status == MedicationAdherenceStatus.UNKNOWN
    assert summary.medications == []


def test_medication_adherence_medication_with_no_reminder_logs_is_unknown():
    request = _request(medications=[_medication(1)])
    summary = build_history_summary(request).history.medication_adherence
    assert summary.overall_status == MedicationAdherenceStatus.UNKNOWN
    assert summary.medications[0].status == MedicationAdherenceStatus.UNKNOWN
    assert summary.medications[0].reminders_sent == 0
    assert summary.medications[0].adherence_rate is None


def test_medication_adherence_high_ack_rate_is_adherent():
    request = _request(
        medications=[_medication(1)],
        medication_reminder_logs=[
            _reminder(1, medication_id=1, acknowledged=True),
            _reminder(2, medication_id=1, acknowledged=True),
            _reminder(3, medication_id=1, acknowledged=True),
            _reminder(4, medication_id=1, acknowledged=True),
            _reminder(5, medication_id=1, acknowledged=False),  # 4/5 = 0.8 -> boundary, adherent
        ],
    )
    summary = build_history_summary(request).history.medication_adherence
    detail = summary.medications[0]
    assert detail.reminders_sent == 5
    assert detail.reminders_acknowledged == 4
    assert detail.adherence_rate == 0.8
    assert detail.status == MedicationAdherenceStatus.ADHERENT
    assert summary.overall_status == MedicationAdherenceStatus.ADHERENT


def test_medication_adherence_mid_ack_rate_is_partially_adherent():
    request = _request(
        medications=[_medication(1)],
        medication_reminder_logs=[
            _reminder(1, medication_id=1, acknowledged=True),
            _reminder(2, medication_id=1, acknowledged=False),  # 1/2 = 0.5 -> boundary, partial
        ],
    )
    summary = build_history_summary(request).history.medication_adherence
    detail = summary.medications[0]
    assert detail.adherence_rate == 0.5
    assert detail.status == MedicationAdherenceStatus.PARTIALLY_ADHERENT
    assert summary.overall_status == MedicationAdherenceStatus.PARTIALLY_ADHERENT


def test_medication_adherence_low_ack_rate_is_non_adherent():
    request = _request(
        medications=[_medication(1)],
        medication_reminder_logs=[
            _reminder(1, medication_id=1, acknowledged=True),
            _reminder(2, medication_id=1, acknowledged=False),
            _reminder(3, medication_id=1, acknowledged=False),
        ],
    )
    summary = build_history_summary(request).history.medication_adherence
    detail = summary.medications[0]
    assert round(detail.adherence_rate, 4) == round(1 / 3, 4)
    assert detail.status == MedicationAdherenceStatus.NON_ADHERENT
    assert summary.overall_status == MedicationAdherenceStatus.NON_ADHERENT


def test_medication_adherence_overall_rollup_picks_worst_status():
    request = _request(
        medications=[_medication(1, "Adherent-Med"), _medication(2, "NonAdherent-Med")],
        medication_reminder_logs=[
            _reminder(1, medication_id=1, acknowledged=True),
            _reminder(2, medication_id=1, acknowledged=True),
            _reminder(3, medication_id=2, acknowledged=False),
            _reminder(4, medication_id=2, acknowledged=False),
        ],
    )
    summary = build_history_summary(request).history.medication_adherence
    statuses = {d.medication_id: d.status for d in summary.medications}
    assert statuses[1] == MedicationAdherenceStatus.ADHERENT
    assert statuses[2] == MedicationAdherenceStatus.NON_ADHERENT
    assert summary.overall_status == MedicationAdherenceStatus.NON_ADHERENT  # worst wins


def test_medication_adherence_ignores_logs_for_unrelated_medication_ids():
    request = _request(
        medications=[_medication(1)],
        medication_reminder_logs=[
            _reminder(1, medication_id=999, acknowledged=True),  # not medication 1
        ],
    )
    summary = build_history_summary(request).history.medication_adherence
    assert summary.medications[0].reminders_sent == 0
    assert summary.medications[0].status == MedicationAdherenceStatus.UNKNOWN


def test_medication_adherence_deterministic_ordering_by_name_then_id():
    request = _request(medications=[_medication(2, "Zeta"), _medication(1, "Alpha")])
    summary = build_history_summary(request).history.medication_adherence
    assert [d.name for d in summary.medications] == ["Alpha", "Zeta"]
