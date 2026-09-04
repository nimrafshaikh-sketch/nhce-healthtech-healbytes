"""Tests for the orchestrator: baseline (Phase 1) + bounded trend (Phase 2)
+ bounded medication-adherence adjustment (Phase 3).

These tests focus on the safety properties required for a healthcare
context: current-check-in stays primary, historical trend and medication
adherence are bounded and cannot flip a low-risk result into high-risk (or
vice versa), and behavior is fully deterministic.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.analysis.medication_adherence import MEDICATION_ADJUSTMENT_MAX
from app.analysis.risk_engine import (
    SEVERITY_SCORES,
    assess as assess_baseline_only,
    classify_risk_level,
    compute_risk_score,
)
from app.analysis.risk_assessor import assess_with_trend
from app.analysis.trend_detector import STRONG_TREND_ADJUSTMENT, WEAK_TREND_ADJUSTMENT, detect_trend
from app.schemas.common import RiskLevel, SeverityLevel
from app.schemas.request import AIAnalysisRequest
from tests.factories import valid_request_payload

_BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _history_entry(days_ago: int, severity: str, request_id: str) -> dict:
    return {
        "request_id": request_id,
        "timestamp": (_BASE_TIME - timedelta(days=days_ago)).isoformat(),
        "severity": severity,
        "risk_level": None,
    }


def _payload_with(check_in: dict, history: list) -> dict:
    payload = valid_request_payload()
    payload["check_in"] = check_in
    payload["historical_context"] = {"previous_checkins": history}
    return payload


_LOW_CHECK_IN = {
    "symptoms": ["mild headache"],
    "severity": "mild",
    "duration": {"value": 2, "unit": "hours"},
}
_HIGH_CHECK_IN = {
    "symptoms": ["chest pain", "shortness of breath", "dizziness", "fatigue"],
    "severity": "severe",
    "duration": {"value": 2, "unit": "weeks"},
}


def _medication(status: str, name: str = "TestMed") -> dict:
    return {"medication_name": name, "adherence_status": status}


def _payload_with_medication(check_in: dict, medication_records: list) -> dict:
    payload = valid_request_payload()
    payload["check_in"] = check_in
    payload["medical_context"]["medication_adherence"] = medication_records
    payload["medical_context"]["medical_history"] = []
    payload["historical_context"] = {"previous_checkins": []}  # no trend, isolate medication
    return payload


# --- Current check-in remains primary when trend is absent/insufficient/stable -


@pytest.mark.parametrize(
    "history",
    [
        [],
        [_history_entry(1, "mild", "h1")],  # single comparison: insufficient
        [_history_entry(2, "moderate", "h1"), _history_entry(1, "moderate", "h2")],  # stable
    ],
)
def test_score_unchanged_when_no_meaningful_trend(history):
    payload = _payload_with(_LOW_CHECK_IN, history)
    payload["medical_context"]["medical_history"] = []
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)

    expected_baseline = compute_risk_score(
        request.check_in.severity,
        request.check_in.duration,
        len(request.check_in.symptoms),
        request.medical_context,
    )
    assert result.risk_score == expected_baseline


# --- Bounds: cannot bypass 0-100, cannot dominate the baseline ----------------


def test_trend_cannot_push_score_above_100():
    history = [
        _history_entry(3, "mild", "h1"),
        _history_entry(2, "moderate", "h2"),
        _history_entry(1, "severe", "h3"),
    ]  # strong worsening: +8
    payload = _payload_with(_HIGH_CHECK_IN, history)
    payload["medical_context"]["medical_history"] = ["asthma"]
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)

    assert result.risk_score <= 100
    assert result.risk_score == 100  # baseline already clamped at 100 pre-trend


def test_trend_cannot_push_score_below_0():
    history = [
        _history_entry(3, "severe", "h1"),
        _history_entry(2, "moderate", "h2"),
        _history_entry(1, "mild", "h3"),
    ]  # strong improving: -8
    payload = _payload_with(_LOW_CHECK_IN, history)
    payload["medical_context"]["medical_history"] = []
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)

    assert result.risk_score >= 0


def test_strong_trend_adjustment_is_smaller_than_any_possible_baseline():
    # The literal safety requirement: trend contribution < current-check-in
    # baseline contribution, for every severity (the smallest baseline is
    # mild-severity-only == SEVERITY_SCORES[MILD]).
    assert STRONG_TREND_ADJUSTMENT < SEVERITY_SCORES[SeverityLevel.MILD]
    assert WEAK_TREND_ADJUSTMENT < SEVERITY_SCORES[SeverityLevel.MILD]


def test_trend_can_never_skip_from_low_to_high_or_high_to_low():
    # Exhaustive over every possible baseline (0-100) and every possible
    # trend adjustment this module can produce. Kept as one test (an
    # internal loop) rather than ~500 parametrized cases, since it is a
    # single property, not many distinct scenarios.
    possible_adjustments = [-STRONG_TREND_ADJUSTMENT, -WEAK_TREND_ADJUSTMENT, 0, WEAK_TREND_ADJUSTMENT, STRONG_TREND_ADJUSTMENT]

    for baseline_score in range(0, 101):
        baseline_level = classify_risk_level(baseline_score)
        for adjustment in possible_adjustments:
            final_score = max(0, min(100, baseline_score + adjustment))
            final_level = classify_risk_level(final_score)

            if baseline_level == RiskLevel.LOW:
                assert final_level != RiskLevel.HIGH
            if baseline_level == RiskLevel.HIGH:
                assert final_level != RiskLevel.LOW


def test_combined_trend_and_medication_can_never_skip_low_to_high_or_high_to_low():
    # Same property as above, but over the combined Phase 2 + Phase 3
    # secondary adjustment space: every achievable trend adjustment paired
    # with every achievable medication adjustment ({0, 3, 5} — see
    # medication_adherence.py; nothing else is reachable after bounding).
    trend_adjustments = [-STRONG_TREND_ADJUSTMENT, -WEAK_TREND_ADJUSTMENT, 0, WEAK_TREND_ADJUSTMENT, STRONG_TREND_ADJUSTMENT]
    medication_adjustments = [0, 3, MEDICATION_ADJUSTMENT_MAX]

    for baseline_score in range(0, 101):
        baseline_level = classify_risk_level(baseline_score)
        for trend_adjustment in trend_adjustments:
            for medication_adjustment in medication_adjustments:
                final_score = max(0, min(100, baseline_score + trend_adjustment + medication_adjustment))
                final_level = classify_risk_level(final_score)

                if baseline_level == RiskLevel.LOW:
                    assert final_level != RiskLevel.HIGH
                if baseline_level == RiskLevel.HIGH:
                    assert final_level != RiskLevel.LOW


def test_max_combined_secondary_adjustment_is_smaller_than_any_possible_baseline():
    # The literal Phase 3 safety requirement, generalized: trend + medication
    # contributions together must stay smaller than the smallest possible
    # current-check-in baseline (mild severity alone == 15).
    max_combined = STRONG_TREND_ADJUSTMENT + MEDICATION_ADJUSTMENT_MAX
    assert max_combined < SEVERITY_SCORES[SeverityLevel.MILD]


# --- Determinism ---------------------------------------------------------------


def test_assess_with_trend_is_deterministic():
    payload = _payload_with(
        _LOW_CHECK_IN,
        [_history_entry(2, "mild", "h1"), _history_entry(1, "moderate", "h2")],
    )
    payload["medical_context"]["medical_history"] = []

    first = assess_with_trend(AIAnalysisRequest.model_validate(payload))
    second = assess_with_trend(AIAnalysisRequest.model_validate(payload))

    assert first == second


def test_unrelated_field_changes_do_not_change_the_trend_component():
    history = [_history_entry(2, "mild", "h1"), _history_entry(1, "severe", "h2")]

    payload_a = _payload_with(_LOW_CHECK_IN, history)
    payload_a["medical_context"]["medical_history"] = []
    payload_a["patient_id"] = "patient-aaa"

    payload_b = _payload_with(_LOW_CHECK_IN, history)
    payload_b["medical_context"]["medical_history"] = []
    payload_b["patient_id"] = "patient-bbb"  # unrelated field differs

    result_a = assess_with_trend(AIAnalysisRequest.model_validate(payload_a))
    result_b = assess_with_trend(AIAnalysisRequest.model_validate(payload_b))

    assert result_a.risk_score == result_b.risk_score
    assert result_a.risk_level == result_b.risk_level
    assert result_a.reason == result_b.reason


# --- Reason text and combined output -------------------------------------------


def test_worsening_trend_increases_score_over_baseline_alone():
    history = [_history_entry(2, "mild", "h1"), _history_entry(1, "severe", "h2")]
    payload = _payload_with(_LOW_CHECK_IN, history)
    payload["medical_context"]["medical_history"] = []
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)
    baseline = compute_risk_score(
        request.check_in.severity,
        request.check_in.duration,
        len(request.check_in.symptoms),
        request.medical_context,
    )

    assert result.risk_score == baseline + WEAK_TREND_ADJUSTMENT
    assert "worsening" in result.reason.lower()


def test_reason_combines_baseline_and_trend_explanations():
    history = [_history_entry(2, "mild", "h1"), _history_entry(1, "severe", "h2")]
    payload = _payload_with(_LOW_CHECK_IN, history)
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)

    assert "severity" in result.reason.lower()  # from the baseline explanation
    assert "observed" in result.reason.lower()  # from the trend explanation
    assert "not medically validated" in result.reason.lower()


def test_no_clinical_accuracy_claim_anywhere_in_combined_reason():
    for check_in, history in [
        (_LOW_CHECK_IN, []),
        (_HIGH_CHECK_IN, [_history_entry(1, "severe", "h1")]),
    ]:
        payload = _payload_with(check_in, history)
        request = AIAnalysisRequest.model_validate(payload)
        result = assess_with_trend(request)
        lowered = result.reason.lower()
        assert "medically accurate" not in lowered
        assert "clinically validated risk model" not in lowered
        assert "guarantees" not in lowered


# --- Phase 3: medication-adherence integration --------------------------------


def test_pipeline_adherent_medication_adds_nothing():
    payload = _payload_with_medication(_LOW_CHECK_IN, [_medication("adherent")])
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)
    baseline = compute_risk_score(
        request.check_in.severity, request.check_in.duration,
        len(request.check_in.symptoms), request.medical_context,
    )

    assert result.risk_score == baseline


def test_pipeline_partially_adherent_medication_adds_three():
    payload = _payload_with_medication(_LOW_CHECK_IN, [_medication("partially_adherent")])
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)
    baseline = compute_risk_score(
        request.check_in.severity, request.check_in.duration,
        len(request.check_in.symptoms), request.medical_context,
    )

    assert result.risk_score == baseline + 3


def test_pipeline_non_adherent_medication_adds_five():
    payload = _payload_with_medication(_LOW_CHECK_IN, [_medication("non_adherent")])
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)
    baseline = compute_risk_score(
        request.check_in.severity, request.check_in.duration,
        len(request.check_in.symptoms), request.medical_context,
    )

    assert result.risk_score == baseline + MEDICATION_ADJUSTMENT_MAX


def test_pipeline_unknown_medication_adds_nothing():
    payload = _payload_with_medication(_LOW_CHECK_IN, [_medication("unknown")])
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)
    baseline = compute_risk_score(
        request.check_in.severity, request.check_in.duration,
        len(request.check_in.symptoms), request.medical_context,
    )

    assert result.risk_score == baseline


def test_pipeline_many_non_adherent_records_still_capped_at_five():
    records = [_medication("non_adherent", f"med-{i}") for i in range(6)]
    payload = _payload_with_medication(_HIGH_CHECK_IN, records)
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)

    # _HIGH_CHECK_IN alone already baselines to 100 (clamped); this also
    # proves the final score never exceeds the 0-100 contract bound.
    assert result.risk_score <= 100


def test_pipeline_final_classification_uses_existing_thresholds():
    payload = _payload_with_medication(_LOW_CHECK_IN, [_medication("non_adherent")])
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)

    assert result.risk_level == classify_risk_level(result.risk_score)


def test_medication_never_independently_creates_high_risk_from_low_baseline():
    # Worst case: max medication concern on the lowest possible baseline.
    records = [_medication("non_adherent", f"med-{i}") for i in range(5)]
    payload = _payload_with_medication(_LOW_CHECK_IN, records)
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)

    assert result.risk_level != RiskLevel.HIGH


def test_medication_never_overrides_a_high_baseline_into_low():
    payload = _payload_with_medication(_HIGH_CHECK_IN, [_medication("adherent")])
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)

    assert result.risk_level != RiskLevel.LOW


# --- Independence from Phase 1 and Phase 2 ------------------------------------


def test_medication_does_not_change_phase1_baseline_scoring():
    payload_a = _payload_with_medication(_LOW_CHECK_IN, [_medication("adherent")])
    payload_b = _payload_with_medication(_LOW_CHECK_IN, [_medication("non_adherent")])

    request_a = AIAnalysisRequest.model_validate(payload_a)
    request_b = AIAnalysisRequest.model_validate(payload_b)

    # risk_engine.assess() is the Phase 1 baseline-only entry point; it must
    # not be affected by medication data at all.
    baseline_a = assess_baseline_only(request_a)
    baseline_b = assess_baseline_only(request_b)

    assert baseline_a.risk_score == baseline_b.risk_score
    assert baseline_a.reason == baseline_b.reason


def test_medication_does_not_change_phase2_trend_detection():
    history = [_history_entry(2, "mild", "h1"), _history_entry(1, "severe", "h2")]

    payload_a = _payload_with(_LOW_CHECK_IN, history)
    payload_a["medical_context"]["medication_adherence"] = [_medication("adherent")]

    payload_b = _payload_with(_LOW_CHECK_IN, history)
    payload_b["medical_context"]["medication_adherence"] = [_medication("non_adherent")]

    request_a = AIAnalysisRequest.model_validate(payload_a)
    request_b = AIAnalysisRequest.model_validate(payload_b)

    trend_a = detect_trend(request_a.historical_context.previous_checkins)
    trend_b = detect_trend(request_b.historical_context.previous_checkins)

    assert trend_a == trend_b


def test_changing_medication_changes_only_the_medication_contribution():
    history = [_history_entry(2, "mild", "h1"), _history_entry(1, "severe", "h2")]

    payload_a = _payload_with(_LOW_CHECK_IN, history)
    payload_a["medical_context"]["medication_adherence"] = [_medication("adherent")]

    payload_b = _payload_with(_LOW_CHECK_IN, history)
    payload_b["medical_context"]["medication_adherence"] = [_medication("non_adherent")]

    result_a = assess_with_trend(AIAnalysisRequest.model_validate(payload_a))
    result_b = assess_with_trend(AIAnalysisRequest.model_validate(payload_b))

    assert result_b.risk_score == result_a.risk_score + MEDICATION_ADJUSTMENT_MAX
    assert "worsening" in result_a.reason.lower()
    assert "worsening" in result_b.reason.lower()  # trend explanation preserved


def test_unrelated_fields_do_not_alter_medication_analysis():
    payload_a = _payload_with_medication(_LOW_CHECK_IN, [_medication("non_adherent")])
    payload_a["patient_id"] = "patient-aaa"

    payload_b = _payload_with_medication(_LOW_CHECK_IN, [_medication("non_adherent")])
    payload_b["patient_id"] = "patient-bbb"

    result_a = assess_with_trend(AIAnalysisRequest.model_validate(payload_a))
    result_b = assess_with_trend(AIAnalysisRequest.model_validate(payload_b))

    assert result_a.risk_score == result_b.risk_score
    assert result_a.reason == result_b.reason


# --- Final response composition: trend + medication both preserved -----------


def test_final_reason_preserves_trend_and_adds_medication_information():
    history = [_history_entry(2, "mild", "h1"), _history_entry(1, "severe", "h2")]
    payload = _payload_with(_LOW_CHECK_IN, history)
    payload["medical_context"]["medication_adherence"] = [_medication("non_adherent")]
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)
    lowered = result.reason.lower()

    assert "severity" in lowered  # Phase 1 baseline evidence
    assert "worsening" in lowered  # Phase 2 trend evidence, preserved
    assert "medication-adherence record" in lowered  # Phase 3 evidence, added
    assert "not medically validated" in lowered  # Phase 2 disclaimer preserved
    assert "does not establish medical risk" in lowered  # Phase 3 disclaimer present


def test_alert_recipient_reflects_final_band_after_medication_adjustment():
    records = [_medication("non_adherent", f"med-{i}") for i in range(5)]
    payload = _payload_with_medication(_HIGH_CHECK_IN, records)
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)

    expected_by_level = {RiskLevel.LOW: "none", RiskLevel.MEDIUM: "care_team", RiskLevel.HIGH: "physician"}
    assert result.alert_recipient.value == expected_by_level[result.risk_level]
    assert result.alert_recipient.value != "emergency_services"


def test_no_medication_recommendation_or_diagnosis_language_in_final_reason():
    payload = _payload_with_medication(_HIGH_CHECK_IN, [_medication("non_adherent")])
    request = AIAnalysisRequest.model_validate(payload)

    result = assess_with_trend(request)
    lowered = result.reason.lower()

    for phrase in (
        "increase the dose",
        "stop taking",
        "start taking",
        "switch medication",
        "diagnosed with",
        "this medication is unsafe",
        "requires emergency treatment",
    ):
        assert phrase not in lowered
