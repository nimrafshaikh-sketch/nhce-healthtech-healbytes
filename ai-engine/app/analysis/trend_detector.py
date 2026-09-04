"""Phase 2 historical-trend heuristic.

This module is a deterministic, rule-based engineering heuristic for
prioritization purposes only. It is explicitly NOT a clinically validated
risk model: it does not predict disease, diagnosis, deterioration,
hospitalization, or emergency events, and its thresholds/weights are
hand-picked engineering defaults for a hackathon MVP, not medically derived
values.

It distinguishes between two kinds of information:

Observed data (taken directly from the request, never interpreted):
    - historical severity values (`PreviousCheckInSummary.severity`)
    - timestamps (`PreviousCheckInSummary.timestamp`), used only to order
      history chronologically
    - the count of historical check-ins supplied

Engineering inference (derived by this module's rules, not measured):
    - `Trend.IMPROVING` / `Trend.WORSENING` / `Trend.STABLE` /
      `Trend.INSUFFICIENT_DATA`
    - `TrendConfidence.WEAK` / `TrendConfidence.STRONG` / `TrendConfidence.NONE`
    - the resulting bounded `score_adjustment`

`historical_risk_level` (also present on `PreviousCheckInSummary`) is
observed data that is intentionally NOT used by this heuristic in Phase 2,
to keep the rule set small, explainable, and free of mixed scales (ordinal
severity vs. risk-level buckets). It remains available in the contract for
a future refinement.

Design rules enforced here (see also `app/analysis/risk_assessor.py`, which
is responsible for bounding how much this module's output can move the
overall score):
    - A trend requires at least `MIN_CHECKINS_FOR_ANY_TREND` historical
      check-ins; a single historical comparison is explicitly treated as
      insufficient evidence, never as a directional trend.
    - A trend only reaches `STRONG` confidence with at least
      `MIN_CHECKINS_FOR_STRONG_TREND` check-ins AND a consistently
      monotonic ordinal-severity sequence; anything else that isn't
      consistently increasing or decreasing is `STABLE`, not a forced
      direction.
    - The resulting score adjustments (`WEAK_TREND_ADJUSTMENT`,
      `STRONG_TREND_ADJUSTMENT`) are small, fixed integers, deliberately
      kept smaller than the smallest possible Phase 1 current-check-in
      baseline score (see `risk_engine.SEVERITY_SCORES[SeverityLevel.MILD]`),
      so historical trend can only nudge, never dominate or override, the
      current reported condition.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List

from app.schemas.common import SeverityLevel
from app.schemas.request import PreviousCheckInSummary

# --- Evidence thresholds (documented, hand-picked; not clinically derived) ----

MIN_CHECKINS_FOR_ANY_TREND = 2
"""Fewer than this many historical check-ins is treated as insufficient
evidence for any direction. A single historical comparison is explicitly
NOT enough to call a trend, per the Phase 2 safety requirement."""

MIN_CHECKINS_FOR_STRONG_TREND = 3
"""At least this many historical check-ins, all moving the same direction,
are required before a trend is labeled `STRONG` rather than `WEAK`."""

# --- Bounded adjustment magnitudes --------------------------------------------
# Deliberately small and fixed. The smallest possible Phase 1 baseline
# contribution is SEVERITY_SCORES[SeverityLevel.MILD] == 15 (see
# risk_engine.py); both adjustments below are kept well under that, so this
# heuristic can only nudge the current-check-in score, never override it.

WEAK_TREND_ADJUSTMENT = 4
STRONG_TREND_ADJUSTMENT = 8

# --- Observed-value ordinal scale ---------------------------------------------
# An engineering ordering only, for comparing consecutive severities. It is
# not a clinical severity index.

SEVERITY_ORDINAL: dict[SeverityLevel, int] = {
    SeverityLevel.MILD: 1,
    SeverityLevel.MODERATE: 2,
    SeverityLevel.SEVERE: 3,
}

TREND_DISCLAIMER = (
    "This trend signal is a deterministic engineering heuristic derived only "
    "from the supplied historical severities; it is not a clinical assessment "
    "of improvement or deterioration and is not medically validated."
)


class Trend(str, Enum):
    IMPROVING = "improving"
    WORSENING = "worsening"
    STABLE = "stable"
    INSUFFICIENT_DATA = "insufficient_data"


class TrendConfidence(str, Enum):
    NONE = "none"
    WEAK = "weak"
    STRONG = "strong"


@dataclass(frozen=True)
class TrendResult:
    """Pure output of the trend heuristic."""

    trend: Trend
    confidence: TrendConfidence
    score_adjustment: int
    observed_count: int
    reason_fragment: str


def _sorted_history(previous_checkins: List[PreviousCheckInSummary]) -> List[PreviousCheckInSummary]:
    """Order observed history chronologically; tie-break on request_id for
    full determinism when timestamps are identical or input order varies."""

    return sorted(previous_checkins, key=lambda c: (c.timestamp, c.request_id))


def _build_reason(
    trend: Trend, confidence: TrendConfidence, observed_count: int, ordinals: List[int], adjustment: int
) -> str:
    if trend is Trend.INSUFFICIENT_DATA:
        body = (
            f"Observed {observed_count} prior check-in(s) in the supplied history — "
            f"insufficient evidence for a directional trend under this heuristic "
            f"(at least {MIN_CHECKINS_FOR_ANY_TREND} historical severity values are "
            "required). Engineering inference: 'insufficient_data'; no score "
            "adjustment applied."
        )
        return f"{body} {TREND_DISCLAIMER}"

    ordinal_seq = ", ".join(str(value) for value in ordinals)

    if trend is Trend.STABLE:
        body = (
            f"Observed {observed_count} prior check-in(s) with an ordinal severity "
            f"sequence of [{ordinal_seq}] (1=mild, 2=moderate, 3=severe) that is not "
            "consistently increasing or decreasing. Engineering inference: 'stable' "
            "reported-severity pattern; no score adjustment applied."
        )
        return f"{body} {TREND_DISCLAIMER}"

    direction_word = "increasing" if trend is Trend.WORSENING else "decreasing"
    sign = "+" if adjustment >= 0 else ""
    body = (
        f"Observed {observed_count} prior check-in(s) with a consistently "
        f"{direction_word} ordinal severity sequence of [{ordinal_seq}] (1=mild, "
        f"2=moderate, 3=severe). Engineering inference: '{trend.value}' "
        f"reported-severity pattern ({confidence.value} signal). Score adjustment "
        f"applied: {sign}{adjustment} point(s), bounded well below the current "
        "check-in's own contribution."
    )
    return f"{body} {TREND_DISCLAIMER}"


def detect_trend(previous_checkins: List[PreviousCheckInSummary]) -> TrendResult:
    """Deterministically classify a historical trend from observed severities.

    Only `previous_checkins` is read; nothing about the current check-in is
    considered here (that composition happens in `risk_assessor.py`).
    """

    observed_count = len(previous_checkins)

    if observed_count < MIN_CHECKINS_FOR_ANY_TREND:
        return TrendResult(
            trend=Trend.INSUFFICIENT_DATA,
            confidence=TrendConfidence.NONE,
            score_adjustment=0,
            observed_count=observed_count,
            reason_fragment=_build_reason(Trend.INSUFFICIENT_DATA, TrendConfidence.NONE, observed_count, [], 0),
        )

    history = _sorted_history(previous_checkins)
    ordinals = [SEVERITY_ORDINAL[entry.severity] for entry in history]
    deltas = [later - earlier for earlier, later in zip(ordinals, ordinals[1:])]

    if all(delta > 0 for delta in deltas):
        trend = Trend.WORSENING
    elif all(delta < 0 for delta in deltas):
        trend = Trend.IMPROVING
    else:
        trend = Trend.STABLE

    if trend is Trend.STABLE:
        confidence = TrendConfidence.NONE
        score_adjustment = 0
    else:
        is_strong = observed_count >= MIN_CHECKINS_FOR_STRONG_TREND
        confidence = TrendConfidence.STRONG if is_strong else TrendConfidence.WEAK
        magnitude = STRONG_TREND_ADJUSTMENT if is_strong else WEAK_TREND_ADJUSTMENT
        score_adjustment = magnitude if trend is Trend.WORSENING else -magnitude

    reason_fragment = _build_reason(trend, confidence, observed_count, ordinals, score_adjustment)

    return TrendResult(
        trend=trend,
        confidence=confidence,
        score_adjustment=score_adjustment,
        observed_count=observed_count,
        reason_fragment=reason_fragment,
    )
