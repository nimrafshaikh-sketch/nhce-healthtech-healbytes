"""Phase 1 deterministic risk-scoring baseline.

This module is a transparent, rule-based engineering baseline used to
prioritize patient check-ins for human follow-up. It is explicitly NOT a
clinical diagnostic system: it does not identify, predict, or imply any
specific medical condition, and its thresholds are hand-picked engineering
defaults for this hackathon MVP, not medically validated values. Nothing it
produces should be read as "this patient has/will have condition X" or as a
guarantee that a situation is or is not an emergency.

The engine exists behind a narrow seam (`assess()` returning a
`RiskAssessment`) so that a future machine-learning model can replace this
rule-based implementation later without changing `app/api/routes.py` or the
public request/response contract in `app/schemas/`.

Fields used as risk signals in Phase 1 (see `app/schemas/request.py`):
    - check_in.severity
    - check_in.duration
    - check_in.symptoms (count only, not symptom identity/content)
    - medical_context.medical_history (presence only, as a small flat modifier)

Fields intentionally NOT analyzed by this module (accepted and validated by
the Phase 0 contract, but read elsewhere in the pipeline, not here):
    - medical_context.medication_adherence — analyzed by
      `app/analysis/medication_adherence.py` (Phase 3), not this baseline.
    - historical_context.previous_checkins — analyzed by
      `app/analysis/trend_detector.py` (Phase 2), not this baseline.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.common import AlertRecipient, DurationUnit, RiskLevel, SeverityLevel
from app.schemas.request import AIAnalysisRequest, Duration, MedicalContext

MODEL_VERSION = "rule-engine-v4"
"""Identifies the deterministic rule-based pipeline version used to produce
a response — the Phase 1 current-check-in baseline in this module, plus any
later bounded adjustment stages composed on top of it (Phase 2 adds a
bounded historical-trend adjustment; Phase 3 adds a bounded
medication-adherence adjustment; Phase 4 adds deterministic follow-up
recommendation; see `app/analysis/risk_assessor.py` and
`app/analysis/follow_up_recommender.py`). This is still not an ML model.
Bump this string whenever the composed pipeline's behavior changes, and use
this single constant everywhere the response `model_version` value is
needed (engine, response builder, tests) so it stays consistent."""

# --- Rule constants ------------------------------------------------------
# These weights and thresholds are an explicit, documented engineering
# baseline chosen for a deterministic MVP demo. They are not derived from
# clinical research and must not be presented as medically validated.

SEVERITY_SCORES: dict[SeverityLevel, int] = {
    SeverityLevel.MILD: 15,
    SeverityLevel.MODERATE: 40,
    SeverityLevel.SEVERE: 70,
}

# Duration is normalized to hours, then bucketed into an additive score.
_HOURS_PER_UNIT: dict[DurationUnit, int] = {
    DurationUnit.HOURS: 1,
    DurationUnit.DAYS: 24,
    DurationUnit.WEEKS: 24 * 7,
}
_DURATION_HOURS_SHORT = 24   # <= 24h:  +0
_DURATION_HOURS_MEDIUM = 72  # <= 72h:  +10
_DURATION_HOURS_LONG = 168   # <= 168h: +20, else +30

_SYMPTOM_COUNT_FEW = 1   # <= 1 symptom:  +0
_SYMPTOM_COUNT_SEVERAL = 3  # <= 3 symptoms: +10, else +20

MEDICAL_HISTORY_MODIFIER = 5
"""Flat bump applied when the patient has any documented medical-history
entry. This only signals that history was disclosed; it does not weigh or
interpret specific conditions."""

RISK_SCORE_MIN = 0
RISK_SCORE_MAX = 100

# Risk-level boundaries (inclusive). Chosen so the three bands are
# reasonably balanced across the achievable 0-100 range.
LOW_UPPER_BOUND = 34     # score 0-34    -> Low
MEDIUM_UPPER_BOUND = 69  # score 35-69   -> Medium
# score 70-100 -> High

ALERT_RECIPIENT_BY_RISK_LEVEL: dict[RiskLevel, AlertRecipient] = {
    RiskLevel.LOW: AlertRecipient.NONE,
    RiskLevel.MEDIUM: AlertRecipient.CARE_TEAM,
    RiskLevel.HIGH: AlertRecipient.PHYSICIAN,
}
"""Placeholder response-field mapping only. Phase 1 does NOT perform, queue,
or trigger any real alert or notification delivery, and never outputs
`emergency_services` automatically."""


@dataclass(frozen=True)
class RiskAssessment:
    """Pure output of the rule engine, before it is wrapped in the response contract."""

    risk_score: int
    risk_level: RiskLevel
    reason: str
    alert_recipient: AlertRecipient


def duration_to_hours(duration: Duration) -> int:
    """Normalize a Duration value+unit pair to a whole number of hours."""

    return duration.value * _HOURS_PER_UNIT[duration.unit]


def score_severity(severity: SeverityLevel) -> int:
    return SEVERITY_SCORES[severity]


def score_duration(duration: Duration) -> int:
    hours = duration_to_hours(duration)
    if hours <= _DURATION_HOURS_SHORT:
        return 0
    if hours <= _DURATION_HOURS_MEDIUM:
        return 10
    if hours <= _DURATION_HOURS_LONG:
        return 20
    return 30


def score_symptom_count(symptom_count: int) -> int:
    if symptom_count <= _SYMPTOM_COUNT_FEW:
        return 0
    if symptom_count <= _SYMPTOM_COUNT_SEVERAL:
        return 10
    return 20


def score_medical_history(medical_context: MedicalContext) -> int:
    return MEDICAL_HISTORY_MODIFIER if medical_context.medical_history else 0


def compute_risk_score(
    severity: SeverityLevel,
    duration: Duration,
    symptom_count: int,
    medical_context: MedicalContext,
) -> int:
    """Sum the individual factor scores and clamp to the 0-100 contract range."""

    total = (
        score_severity(severity)
        + score_duration(duration)
        + score_symptom_count(symptom_count)
        + score_medical_history(medical_context)
    )
    return max(RISK_SCORE_MIN, min(RISK_SCORE_MAX, total))


def classify_risk_level(risk_score: int) -> RiskLevel:
    """Deterministically map a 0-100 score onto Low / Medium / High."""

    if risk_score <= LOW_UPPER_BOUND:
        return RiskLevel.LOW
    if risk_score <= MEDIUM_UPPER_BOUND:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


def map_alert_recipient(risk_level: RiskLevel) -> AlertRecipient:
    """Placeholder response classification only — see module docstring."""

    return ALERT_RECIPIENT_BY_RISK_LEVEL[risk_level]


def build_reason(
    severity: SeverityLevel,
    severity_score: int,
    duration_hours: int,
    duration_score: int,
    symptom_count: int,
    symptom_score: int,
    history_score: int,
) -> str:
    """Compose a deterministic explanation from the actual factors used.

    Every sentence reflects a real input to the scoring function above; none
    of this text is a fabricated clinical explanation or diagnosis.
    """

    parts = [f"Reported severity '{severity.value}' contributed {severity_score} point(s)."]

    if duration_score > 0:
        parts.append(
            f"Symptom duration of {duration_hours} hour(s) contributed an "
            f"additional {duration_score} point(s)."
        )
    else:
        parts.append("Symptom duration was short enough to add no additional points.")

    if symptom_score > 0:
        parts.append(
            f"Reporting {symptom_count} symptoms together contributed an "
            f"additional {symptom_score} point(s)."
        )
    else:
        parts.append("Only one symptom was reported, adding no additional points.")

    if history_score > 0:
        parts.append(
            f"Documented medical history is present and added a minor "
            f"{history_score}-point modifier."
        )

    parts.append(
        "This is a deterministic, rule-based MVP baseline used to prioritize "
        "follow-up, not a medical diagnosis or clinically validated risk assessment."
    )
    return " ".join(parts)


def assess(request: AIAnalysisRequest) -> RiskAssessment:
    """Run the full Phase 1 rule engine against a validated request.

    Only `request.check_in` and `request.medical_context.medical_history`
    are read. `medication_adherence` and `historical_context` are
    intentionally ignored in Phase 1 (see module docstring).
    """

    severity = request.check_in.severity
    duration = request.check_in.duration
    symptom_count = len(request.check_in.symptoms)
    medical_context = request.medical_context

    severity_score = score_severity(severity)
    duration_score = score_duration(duration)
    symptom_score = score_symptom_count(symptom_count)
    history_score = score_medical_history(medical_context)

    risk_score = compute_risk_score(severity, duration, symptom_count, medical_context)
    risk_level = classify_risk_level(risk_score)
    reason = build_reason(
        severity,
        severity_score,
        duration_to_hours(duration),
        duration_score,
        symptom_count,
        symptom_score,
        history_score,
    )
    alert_recipient = map_alert_recipient(risk_level)

    return RiskAssessment(
        risk_score=risk_score,
        risk_level=risk_level,
        reason=reason,
        alert_recipient=alert_recipient,
    )
