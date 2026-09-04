"""Phase 5 controlled AI explanation layer.

This module provides human-readable, care-team-friendly explanations of the
already-computed deterministic risk assessment. It is explicitly a downstream
presentation and explainability enhancement for hackathon demo and clinical
coordination purposes — NOT a clinical diagnostic tool, NOT a treatment
planner, and NOT a secondary risk engine.

Architectural principles enforced here:
    1. The deterministic engine (Phases 1-4) is the absolute source of truth.
    2. This module is strictly observational/downstream: it NEVER calculates,
       modifies, or feeds back into `risk_score`, `risk_level`, `alert_recipient`,
       or `follow_up_action`.
    3. A deterministic fallback explanation is ALWAYS available and is the
       default operational path when no LLM provider is configured, or if a
       provider fails, times out, or produces unsafe output.
    4. Strict output validation: any candidate explanation is checked for
       length, risk-level consistency (no contradictions), and forbidden
       clinical claims (diagnoses, treatment prescriptions, medication
       changes, emergency-service instructions).
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional, Protocol

from app.analysis.risk_engine import RiskAssessment
from app.schemas.common import AlertRecipient, RiskLevel

logger = logging.getLogger(__name__)

MAX_EXPLANATION_LENGTH = 1000

# Representative forbidden clinical / treatment / emergency phrases
FORBIDDEN_EXPLANATION_PHRASES: List[str] = [
    "diagnosed with",
    "confirmed diagnosis",
    "has a disease",
    "will develop",
    "will be hospitalized",
    "guarantees an emergency",
    "medically accurate",
    "clinically validated",
    "prescribe",
    "treatment plan",
    "administer",
    "increase the dose",
    "decrease the dose",
    "stop taking",
    "start taking",
    "switch medication",
    "this medication is unsafe",
    "emergency services",
    "call 911",
    "call 999",
    "call 112",
    "ambulance",
    "emergency room",
    "emergency department",
    "requires emergency treatment",
    "life-threatening",
]


class ExplanationProvider(Protocol):
    """Protocol for optional LLM / AI explanation providers."""

    def generate_explanation(
        self,
        risk_level: RiskLevel,
        risk_score: float,
        reason: str,
        alert_recipient: AlertRecipient,
        follow_up_action: Optional[str] = None,
    ) -> str:
        ...


def generate_fallback_explanation(
    risk_level: RiskLevel,
    risk_score: float,
    follow_up_action: Optional[str] = None,
) -> str:
    """Generate a pure, deterministic, safe fallback explanation based strictly
    on the supplied risk assessment and care-coordination action.

    Matches the required contract structure:
    "The assessment indicates {risk_level.value} risk (score: {score:.1f}/100) based on the deterministic evaluation of reported symptoms, duration, and context. {follow_up_action}"
    """
    base = (
        f"The assessment indicates {risk_level.value} risk (score: {risk_score:.1f}/100) "
        "based on the deterministic evaluation of reported symptoms, duration, and context."
    )
    if follow_up_action and follow_up_action.strip():
        return f"{base} {follow_up_action.strip()}"
    return base


def validate_explanation(explanation: str, expected_risk_level: RiskLevel) -> bool:
    """Validate a candidate explanation against strict safety and consistency rules.

    Rejects:
      - Non-string, empty, or whitespace-only text
      - Overly long output (> MAX_EXPLANATION_LENGTH)
      - Contradictory risk level claims (e.g. Low claiming High/Medium)
      - Forbidden clinical, diagnostic, treatment, dosage, or emergency phrases
    """
    if not isinstance(explanation, str):
        return False

    cleaned = explanation.strip()
    if not cleaned:
        return False

    if len(cleaned) > MAX_EXPLANATION_LENGTH:
        return False

    lowered = cleaned.lower()

    # Contradiction check: ensure explanation does not contradict expected risk level
    if expected_risk_level == RiskLevel.LOW:
        if re.search(r"\bmedium\s+risk\b", lowered) or re.search(r"\bhigh\s+risk\b", lowered):
            return False
    elif expected_risk_level == RiskLevel.MEDIUM:
        if re.search(r"\blow\s+risk\b", lowered) or re.search(r"\bhigh\s+risk\b", lowered):
            return False
    elif expected_risk_level == RiskLevel.HIGH:
        if re.search(r"\blow\s+risk\b", lowered) or re.search(r"\bmedium\s+risk\b", lowered):
            return False

    # Forbidden phrase check
    for phrase in FORBIDDEN_EXPLANATION_PHRASES:
        if phrase in lowered:
            return False

    return True


class ExplanationService:
    """Service encapsulating explanation generation with failure isolation."""

    def __init__(self, provider: Optional[ExplanationProvider] = None):
        self._provider = provider

    def generate_explanation(
        self,
        assessment: RiskAssessment,
        follow_up_action: Optional[str] = None,
    ) -> str:
        """Generate a validated explanation, gracefully falling back to deterministic
        template on any provider failure, timeout, or safety validation failure.
        """
        fallback = generate_fallback_explanation(
            risk_level=assessment.risk_level,
            risk_score=float(assessment.risk_score),
            follow_up_action=follow_up_action,
        )

        if self._provider is None:
            return fallback

        try:
            candidate = self._provider.generate_explanation(
                risk_level=assessment.risk_level,
                risk_score=float(assessment.risk_score),
                reason=assessment.reason,
                alert_recipient=assessment.alert_recipient,
                follow_up_action=follow_up_action,
            )
            if validate_explanation(candidate, assessment.risk_level):
                return candidate.strip()
            logger.warning(
                "Explanation provider output failed safety validation; using fallback."
            )
        except Exception:
            logger.warning(
                "Explanation provider raised an exception; using fallback.",
                exc_info=True,
            )

        return fallback


_default_explanation_service = ExplanationService()


def generate_explanation(
    assessment: RiskAssessment,
    follow_up_action: Optional[str] = None,
    service: Optional[ExplanationService] = None,
) -> str:
    """Convenience helper to generate an explanation using either the default
    or a custom configured ExplanationService.
    """
    active_service = service or _default_explanation_service
    return active_service.generate_explanation(assessment, follow_up_action)
