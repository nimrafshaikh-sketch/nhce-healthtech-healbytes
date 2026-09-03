"""Phase 6 deterministic risk-scoring baseline, rebuilt against the agreed
backend wire contract (`backend/apps/checkins/ai_client.py`,
`feature/backend` branch).

This module is a transparent, rule-based engineering baseline used to
prioritize patient check-ins for human follow-up. It is explicitly NOT a
clinical diagnostic system: it does not identify, predict, or imply any
specific medical condition, and its thresholds are hand-picked engineering
defaults for this hackathon MVP, not medically validated values.

The engine exists behind a narrow seam (`assess()` returning a
`RiskAssessment`) so that a future machine-learning model can replace this
rule-based implementation later without changing `app/api/routes.py` or the
public request/response contract in `app/schemas/`.

Fields used as risk signals (see `app/schemas/request.py`):
    - pain_level (0-10 self-reported scale; assumed range, see
      `app/schemas/request.py::PAIN_LEVEL_MIN/MAX` — not confirmed by the
      backend contract)
    - symptoms (count only, not symptom identity/content)

Fields intentionally NOT scored yet, even though the contract accepts them:
    - mood — no agreed vocabulary or risk mapping exists for this field.
      Scoring free-text/choice mood without a defined scale would be
      inventing clinical judgment, not implementing an agreed rule, so it
      is carried through into `reason` as "received but not scored" and
      left for a deliberate future decision.
    - vitals — the contract defines no sub-schema (units, expected keys, or
      normal ranges) for this field, so there is nothing deterministic to
      score against. Same treatment as `mood`.
    - notes — free text; scoring it would require NLP/LLM inference, which
      is explicitly out of scope for this phase.
This mirrors the existing pattern already used elsewhere in this codebase
for accepted-but-unscored fields (e.g. `medication_name` in the pre-Phase-6
contract) rather than being a new convention.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.common import NotificationRecipient, RiskLevel
from app.schemas.request import AIAnalysisRequest

MODEL_VERSION = "rule-engine-v6"
"""Identifies the deterministic rule pipeline version. Not part of the
agreed wire response contract (see `app/schemas/response.py`), but kept as
an internal constant for logs and future diagnostics."""

# --- Rule constants ------------------------------------------------------
# Hand-picked engineering defaults for a deterministic MVP demo. Not derived
# from clinical research and must not be presented as medically validated.

RISK_SCORE_MIN = 0
RISK_SCORE_MAX = 100

# Pain level (0-10) bucketed into an additive score, out of a 75-point share
# of the 0-100 total (the remaining 25 points come from symptom count).
_PAIN_BUCKETS: tuple[tuple[int, int], ...] = (
    (2, 0),   # 0-2: no meaningful contribution
    (5, 25),  # 3-5: mild-to-moderate
    (8, 50),  # 6-8: significant
    (10, 75),  # 9-10: severe
)

_SYMPTOM_COUNT_FEW = 1      # <= 1 symptom:  +0
_SYMPTOM_COUNT_SEVERAL = 3  # <= 3 symptoms: +10, else +25

# Risk-level boundaries (inclusive), unchanged in spirit from earlier phases.
LOW_UPPER_BOUND = 34     # score 0-34    -> low
MEDIUM_UPPER_BOUND = 69  # score 35-69   -> medium
# score 70-100 -> high

NOTIFICATION_RECIPIENT_BY_RISK_LEVEL: dict[RiskLevel, NotificationRecipient] = {
    RiskLevel.LOW: NotificationRecipient.NONE,
    RiskLevel.MEDIUM: NotificationRecipient.CARETAKER,
    RiskLevel.HIGH: NotificationRecipient.DOCTOR,
}
"""Informational-only mapping — see `NotificationRecipient` docstring. The
backend's own `apps.alerts.rules` is the actual routing decision-maker."""


@dataclass(frozen=True)
class RiskAssessment:
    """Pure output of the rule engine, before it is wrapped in the response contract."""

    risk_score: int  # internal 0-100 scale; converted to 0.0-1.0 at the response boundary
    risk_level: RiskLevel
    reason: str
    notification_recipient: NotificationRecipient


def score_pain_level(pain_level: int | None) -> int:
    if pain_level is None:
        return 0
    for upper_bound, score in _PAIN_BUCKETS:
        if pain_level <= upper_bound:
            return score
    return _PAIN_BUCKETS[-1][1]


def score_symptom_count(symptom_count: int) -> int:
    if symptom_count <= _SYMPTOM_COUNT_FEW:
        return 0
    if symptom_count <= _SYMPTOM_COUNT_SEVERAL:
        return 10
    return 25


def compute_risk_score(pain_level: int | None, symptom_count: int) -> int:
    """Sum the individual factor scores and clamp to the 0-100 contract range."""

    total = score_pain_level(pain_level) + score_symptom_count(symptom_count)
    return max(RISK_SCORE_MIN, min(RISK_SCORE_MAX, total))


def classify_risk_level(risk_score: int) -> RiskLevel:
    """Deterministically map a 0-100 score onto low / medium / high."""

    if risk_score <= LOW_UPPER_BOUND:
        return RiskLevel.LOW
    if risk_score <= MEDIUM_UPPER_BOUND:
        return RiskLevel.MEDIUM
    return RiskLevel.HIGH


def map_notification_recipient(risk_level: RiskLevel) -> NotificationRecipient:
    """Placeholder response classification only — see module docstring."""

    return NOTIFICATION_RECIPIENT_BY_RISK_LEVEL[risk_level]


def build_reason(
    pain_level: int | None,
    pain_score: int,
    symptom_count: int,
    symptom_score: int,
    mood: str | None,
    vitals_present: bool,
    notes_present: bool,
) -> str:
    """Compose a deterministic explanation from the actual factors used.

    Every sentence reflects a real input to the scoring function above; none
    of this text is a fabricated clinical explanation or diagnosis.
    """

    parts: list[str] = []

    if pain_level is None:
        parts.append("No pain level was reported, so it contributed 0 point(s).")
    else:
        parts.append(f"Reported pain level {pain_level}/10 contributed {pain_score} point(s).")

    if symptom_count == 0:
        parts.append("No symptoms were reported, contributing 0 point(s).")
    elif symptom_score > 0:
        parts.append(
            f"Reporting {symptom_count} symptom(s) together contributed an "
            f"additional {symptom_score} point(s)."
        )
    else:
        parts.append("Only one symptom was reported, adding no additional points.")

    unscored = []
    if mood:
        unscored.append("mood")
    if vitals_present:
        unscored.append("vitals")
    if notes_present:
        unscored.append("notes")
    if unscored:
        parts.append(
            f"{', '.join(unscored)} data was received but is not yet scored by this "
            "deterministic baseline (no agreed scoring rule for these fields)."
        )

    parts.append(
        "This is a deterministic, rule-based MVP baseline used to prioritize "
        "follow-up, not a medical diagnosis or clinically validated risk assessment."
    )
    return " ".join(parts)


def assess(request: AIAnalysisRequest) -> RiskAssessment:
    """Run the full rule engine against a validated request.

    Only `pain_level` and `symptoms` (count) are scored. `mood`, `vitals`,
    and `notes` are validated and carried through into `reason` as received
    but unscored — see module docstring.
    """

    symptom_count = len(request.symptoms)

    pain_score = score_pain_level(request.pain_level)
    symptom_score = score_symptom_count(symptom_count)

    risk_score = compute_risk_score(request.pain_level, symptom_count)
    risk_level = classify_risk_level(risk_score)
    reason = build_reason(
        request.pain_level,
        pain_score,
        symptom_count,
        symptom_score,
        request.mood,
        bool(request.vitals),
        bool(request.notes),
    )
    notification_recipient = map_notification_recipient(risk_level)

    return RiskAssessment(
        risk_score=risk_score,
        risk_level=risk_level,
        reason=reason,
        notification_recipient=notification_recipient,
    )
