"""Orchestrator: Phase 1 current-check-in baseline + a bounded, evidence-
gated historical-trend adjustment (Phase 2) + a bounded medication-
adherence adjustment (Phase 3).

Design principle (explicitly required, unchanged since Phase 2): the
current check-in is the primary signal; historical trend and medication
adherence are strictly smaller, secondary/contextual adjustments on top of
it. This module is the single place that composes all three so that any of
them — the baseline scorer in `risk_engine.py`, the trend heuristic in
`trend_detector.py`, or the medication heuristic in
`medication_adherence.py` — can be improved or replaced independently
without touching `app/api/routes.py` or the response schema.

Neither this module nor its inputs claim clinical validity: see the module
docstrings of `risk_engine.py`, `trend_detector.py`, and
`medication_adherence.py` for the full disclaimers, which are also carried
through into the generated `reason` text returned here.
"""

from __future__ import annotations

from app.analysis.medication_adherence import assess_medication_adherence
from app.analysis.risk_engine import (
    RISK_SCORE_MAX,
    RISK_SCORE_MIN,
    RiskAssessment,
    build_reason as build_baseline_reason,
    classify_risk_level,
    compute_risk_score,
    duration_to_hours,
    map_alert_recipient,
    score_duration,
    score_medical_history,
    score_severity,
    score_symptom_count,
)
from app.analysis.trend_detector import detect_trend
from app.schemas.request import AIAnalysisRequest


def assess_with_trend(request: AIAnalysisRequest) -> RiskAssessment:
    """Compute the Phase 1 baseline, then apply the bounded Phase 2 (trend)
    and Phase 3 (medication-adherence) adjustments on top of it, and return
    the combined result.

    The baseline is computed first and independently classified/reasoned
    about (identical to Phase 1's own `risk_engine.assess`); the trend and
    medication adjustments are then added and the *combined* score is what
    gets clamped and (re-)classified. Both adjustments are small and
    bounded, and even together (trend up to ±8, medication up to +5) their
    combined magnitude stays below the smallest possible baseline score
    (15) — so this composition can shift the result by at most one risk
    band. It can never turn an obviously low current-risk check-in into a
    high-risk one, or an obviously high one into a low-risk one, based
    solely on historical trend and/or medication adherence.
    """

    check_in = request.check_in
    medical_context = request.medical_context

    severity_score = score_severity(check_in.severity)
    duration_score = score_duration(check_in.duration)
    symptom_count = len(check_in.symptoms)
    symptom_score = score_symptom_count(symptom_count)
    history_score = score_medical_history(medical_context)

    baseline_score = compute_risk_score(
        check_in.severity, check_in.duration, symptom_count, medical_context
    )
    baseline_reason = build_baseline_reason(
        check_in.severity,
        severity_score,
        duration_to_hours(check_in.duration),
        duration_score,
        symptom_count,
        symptom_score,
        history_score,
    )

    trend_result = detect_trend(request.historical_context.previous_checkins)
    medication_result = assess_medication_adherence(medical_context.medication_adherence)

    combined_score = (
        baseline_score + trend_result.score_adjustment + medication_result.score_adjustment
    )
    final_score = max(RISK_SCORE_MIN, min(RISK_SCORE_MAX, combined_score))
    risk_level = classify_risk_level(final_score)
    alert_recipient = map_alert_recipient(risk_level)

    reason = (
        f"{baseline_reason} {trend_result.reason_fragment} "
        f"{medication_result.reason_fragment}"
    )

    return RiskAssessment(
        risk_score=final_score,
        risk_level=risk_level,
        reason=reason,
        alert_recipient=alert_recipient,
    )
