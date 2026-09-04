"""Tests for the Phase 2 historical-trend heuristic.

`detect_trend` is pure and reads only a list of `PreviousCheckInSummary`
objects — no request, no current check-in, no FastAPI — so it is tested
fully in isolation here, independent of the rest of the engine.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.analysis.trend_detector import (
    MIN_CHECKINS_FOR_ANY_TREND,
    MIN_CHECKINS_FOR_STRONG_TREND,
    STRONG_TREND_ADJUSTMENT,
    WEAK_TREND_ADJUSTMENT,
    Trend,
    TrendConfidence,
    detect_trend,
)
from app.schemas.common import SeverityLevel
from app.schemas.request import PreviousCheckInSummary

_BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)

# Forbidden affirmative clinical claims: none of these should ever appear in
# reason text produced by this module (case-insensitive substring match).
_FORBIDDEN_CLAIM_PHRASES = [
    "diagnosed with",
    "has a disease",
    "will develop",
    "will be hospitalized",
    "guarantees an emergency",
    "medically accurate",
    "clinically validated risk model",
    "predicts that",
    "confirmed diagnosis",
]


def _checkin(days_ago: int, severity: SeverityLevel, request_id: str | None = None) -> PreviousCheckInSummary:
    return PreviousCheckInSummary(
        request_id=request_id or f"req-{days_ago}",
        timestamp=_BASE_TIME - timedelta(days=days_ago),
        severity=severity,
        risk_level=None,
    )


# --- Evidence sufficiency ------------------------------------------------------


def test_no_history_is_insufficient_data():
    result = detect_trend([])
    assert result.trend == Trend.INSUFFICIENT_DATA
    assert result.confidence == TrendConfidence.NONE
    assert result.score_adjustment == 0
    assert result.observed_count == 0


def test_single_history_entry_is_insufficient_data_not_a_trend():
    # A single historical comparison must never be classified as a
    # directional trend, per the Phase 2 safety requirement.
    result = detect_trend([_checkin(days_ago=1, severity=SeverityLevel.SEVERE)])
    assert result.trend == Trend.INSUFFICIENT_DATA
    assert result.score_adjustment == 0
    assert MIN_CHECKINS_FOR_ANY_TREND == 2  # documents the threshold this test relies on


# --- Directional classification -------------------------------------------------


def test_two_increasing_entries_is_weak_worsening():
    history = [_checkin(2, SeverityLevel.MILD), _checkin(1, SeverityLevel.MODERATE)]
    result = detect_trend(history)
    assert result.trend == Trend.WORSENING
    assert result.confidence == TrendConfidence.WEAK
    assert result.score_adjustment == WEAK_TREND_ADJUSTMENT


def test_two_decreasing_entries_is_weak_improving():
    history = [_checkin(2, SeverityLevel.SEVERE), _checkin(1, SeverityLevel.MODERATE)]
    result = detect_trend(history)
    assert result.trend == Trend.IMPROVING
    assert result.confidence == TrendConfidence.WEAK
    assert result.score_adjustment == -WEAK_TREND_ADJUSTMENT


def test_two_equal_entries_is_stable():
    history = [_checkin(2, SeverityLevel.MODERATE), _checkin(1, SeverityLevel.MODERATE)]
    result = detect_trend(history)
    assert result.trend == Trend.STABLE
    assert result.confidence == TrendConfidence.NONE
    assert result.score_adjustment == 0


def test_three_increasing_entries_is_strong_worsening():
    history = [_checkin(3, SeverityLevel.MILD), _checkin(2, SeverityLevel.MODERATE), _checkin(1, SeverityLevel.SEVERE)]
    result = detect_trend(history)
    assert result.trend == Trend.WORSENING
    assert result.confidence == TrendConfidence.STRONG
    assert result.score_adjustment == STRONG_TREND_ADJUSTMENT
    assert MIN_CHECKINS_FOR_STRONG_TREND == 3  # documents the threshold this test relies on


def test_three_decreasing_entries_is_strong_improving():
    history = [_checkin(3, SeverityLevel.SEVERE), _checkin(2, SeverityLevel.MODERATE), _checkin(1, SeverityLevel.MILD)]
    result = detect_trend(history)
    assert result.trend == Trend.IMPROVING
    assert result.confidence == TrendConfidence.STRONG
    assert result.score_adjustment == -STRONG_TREND_ADJUSTMENT


def test_mixed_direction_history_is_stable_not_forced_directional():
    history = [_checkin(3, SeverityLevel.MILD), _checkin(2, SeverityLevel.SEVERE), _checkin(1, SeverityLevel.MODERATE)]
    result = detect_trend(history)
    assert result.trend == Trend.STABLE
    assert result.score_adjustment == 0


def test_strong_adjustment_is_larger_than_weak_but_both_are_small():
    assert STRONG_TREND_ADJUSTMENT > WEAK_TREND_ADJUSTMENT > 0
    # Both must stay smaller than the smallest possible current-check-in
    # baseline contribution (mild severity == 15); see risk_engine.py.
    assert STRONG_TREND_ADJUSTMENT < 15


# --- Determinism and independence from unrelated input -------------------------


def test_same_history_produces_same_result():
    history = [_checkin(3, SeverityLevel.MILD), _checkin(2, SeverityLevel.MODERATE), _checkin(1, SeverityLevel.SEVERE)]
    first = detect_trend(list(history))
    second = detect_trend(list(history))
    assert first == second


def test_input_order_does_not_affect_result():
    # The detector sorts by timestamp internally, so shuffled input order
    # must produce the identical result to chronological input order.
    chronological = [_checkin(3, SeverityLevel.MILD), _checkin(2, SeverityLevel.MODERATE), _checkin(1, SeverityLevel.SEVERE)]
    shuffled = [chronological[2], chronological[0], chronological[1]]

    assert detect_trend(chronological) == detect_trend(shuffled)


# --- Reason text: observed vs. inference, and no clinical claims --------------


@pytest.mark.parametrize(
    "history",
    [
        [],
        [_checkin(1, SeverityLevel.SEVERE)],
        [_checkin(2, SeverityLevel.MILD), _checkin(1, SeverityLevel.MODERATE)],
        [_checkin(2, SeverityLevel.MODERATE), _checkin(1, SeverityLevel.MODERATE)],
        [_checkin(3, SeverityLevel.MILD), _checkin(2, SeverityLevel.MODERATE), _checkin(1, SeverityLevel.SEVERE)],
        [_checkin(3, SeverityLevel.MILD), _checkin(2, SeverityLevel.SEVERE), _checkin(1, SeverityLevel.MODERATE)],
    ],
)
def test_reason_never_contains_forbidden_clinical_claims(history):
    result = detect_trend(history)
    lowered = result.reason_fragment.lower()
    for phrase in _FORBIDDEN_CLAIM_PHRASES:
        assert phrase not in lowered


def test_reason_always_carries_the_non_clinical_disclaimer():
    for history in (
        [],
        [_checkin(2, SeverityLevel.MILD), _checkin(1, SeverityLevel.SEVERE)],
        [_checkin(2, SeverityLevel.MODERATE), _checkin(1, SeverityLevel.MODERATE)],
    ):
        result = detect_trend(history)
        assert "not medically validated" in result.reason_fragment.lower()


def test_reason_reflects_worsening_trend():
    history = [_checkin(3, SeverityLevel.MILD), _checkin(2, SeverityLevel.MODERATE), _checkin(1, SeverityLevel.SEVERE)]
    result = detect_trend(history)
    assert "worsening" in result.reason_fragment.lower()
    assert "improving" not in result.reason_fragment.lower()


def test_reason_reflects_improving_trend():
    history = [_checkin(3, SeverityLevel.SEVERE), _checkin(2, SeverityLevel.MODERATE), _checkin(1, SeverityLevel.MILD)]
    result = detect_trend(history)
    assert "improving" in result.reason_fragment.lower()
    assert "worsening" not in result.reason_fragment.lower()


def test_reason_reflects_insufficient_data():
    result = detect_trend([_checkin(1, SeverityLevel.SEVERE)])
    assert "insufficient_data" in result.reason_fragment.lower()


def test_reason_reflects_stable():
    history = [_checkin(2, SeverityLevel.MODERATE), _checkin(1, SeverityLevel.MODERATE)]
    result = detect_trend(history)
    assert "stable" in result.reason_fragment.lower()


def test_reason_uses_observed_and_inference_language():
    history = [_checkin(3, SeverityLevel.MILD), _checkin(2, SeverityLevel.MODERATE), _checkin(1, SeverityLevel.SEVERE)]
    result = detect_trend(history)
    lowered = result.reason_fragment.lower()
    assert "observed" in lowered
    assert "engineering inference" in lowered
