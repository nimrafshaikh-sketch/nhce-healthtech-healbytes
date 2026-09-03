"""Phase 4 deterministic follow-up recommendation engine.

This module is a transparent, rule-based engineering heuristic for care
coordination and follow-up prioritization only. It is explicitly NOT a
clinical diagnostic system, a treatment plan, a prescription engine, or a
substitute for medical judgment. It never performs a network call, never
calls an LLM or an external API, never touches a database, and never sends a
notification — it is a pure function over the final `RiskLevel` produced by
the preceding pipeline stages (Phase 1 baseline + Phase 2 trend + Phase 3
medication adherence).

Design rules enforced here:
    - Input is the final, classified `RiskLevel` (`Low`, `Medium`, `High`)
      after all scoring and adjustments are complete.
    - This module does NOT modify, recalculate, or feed back into
      `risk_score` or `risk_level`. The risk assessment is read-only.
    - Output is a deterministic, non-clinical care-coordination action string:
        * `Low` -> Routine monitoring action.
        * `Medium` -> Closer care-team review action.
        * `High` -> Prompt physician review action.
    - Even for `High` risk, this module never instructs emergency services,
      hospitalization, or urgent interventions — the system does not have
      sufficient clinical context for such recommendations.
    - This module never generates medical diagnoses, treatment instructions,
      or medication changes.
"""

from __future__ import annotations

from typing import Dict

from app.schemas.common import RiskLevel

FOLLOW_UP_RECOMMENDATIONS: Dict[RiskLevel, str] = {
    RiskLevel.LOW: "Continue routine monitoring and complete the next scheduled check-in.",
    RiskLevel.MEDIUM: "Care-team review and closer follow-up are recommended.",
    RiskLevel.HIGH: "Prompt physician review is recommended based on the current risk assessment.",
}
"""Deterministic care-coordination mapping from final risk level to recommended
follow-up action. These strings are engineering defaults for MVP care coordination
and are not clinical treatment prescriptions."""


def recommend_follow_up(risk_level: RiskLevel) -> str:
    """Deterministically map a final RiskLevel onto a care-coordination follow-up action.

    This function is pure, stateless, and has no side effects.
    """
    return FOLLOW_UP_RECOMMENDATIONS[risk_level]
