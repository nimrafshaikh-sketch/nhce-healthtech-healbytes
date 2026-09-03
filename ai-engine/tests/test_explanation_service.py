"""Tests for the Phase 5 controlled AI explanation layer.

`ExplanationService` provides human-readable explanations of the already-computed
deterministic risk assessment. These tests verify the deterministic fallback,
provider abstraction, safety validation, failure isolation, and observational
downstream integrity.
"""

import inspect
from typing import Optional

import pytest

from app.analysis import explanation_service
from app.analysis.explanation_service import (
    FORBIDDEN_EXPLANATION_PHRASES,
    MAX_EXPLANATION_LENGTH,
    ExplanationService,
    generate_explanation,
    generate_fallback_explanation,
    validate_explanation,
)
from app.analysis.risk_engine import RiskAssessment
from app.schemas.common import AlertRecipient, RiskLevel


def _make_assessment(
    level: RiskLevel = RiskLevel.LOW,
    score: int = 15,
    reason: str = "Test reason.",
    recipient: AlertRecipient = AlertRecipient.NONE,
) -> RiskAssessment:
    return RiskAssessment(
        risk_score=score,
        risk_level=level,
        reason=reason,
        alert_recipient=recipient,
    )


# --- Deterministic fallback tests --------------------------------------------


def test_fallback_explanation_low_risk():
    action = "Continue routine monitoring and complete the next scheduled check-in."
    text = generate_fallback_explanation(RiskLevel.LOW, 15.0, action)
    assert "Low risk" in text
    assert "(score: 15.0/100)" in text
    assert action in text


def test_fallback_explanation_medium_risk():
    action = "Care-team review and closer follow-up are recommended."
    text = generate_fallback_explanation(RiskLevel.MEDIUM, 60.0, action)
    assert "Medium risk" in text
    assert "(score: 60.0/100)" in text
    assert action in text


def test_fallback_explanation_high_risk():
    action = "Prompt physician review is recommended based on the current risk assessment."
    text = generate_fallback_explanation(RiskLevel.HIGH, 85.0, action)
    assert "High risk" in text
    assert "(score: 85.0/100)" in text
    assert action in text


def test_fallback_explanation_without_follow_up_action():
    text = generate_fallback_explanation(RiskLevel.LOW, 15.0, None)
    assert "Low risk" in text
    assert "(score: 15.0/100)" in text
    assert not text.endswith("None")


def test_fallback_is_purely_deterministic():
    first = generate_fallback_explanation(RiskLevel.MEDIUM, 50.0, "Action A")
    second = generate_fallback_explanation(RiskLevel.MEDIUM, 50.0, "Action A")
    assert first == second


def test_default_service_uses_fallback_when_no_provider():
    service = ExplanationService(provider=None)
    assessment = _make_assessment(RiskLevel.LOW, 15)
    action = "Continue routine monitoring."
    result = service.generate_explanation(assessment, action)
    assert result == generate_fallback_explanation(RiskLevel.LOW, 15.0, action)


# --- Provider success tests --------------------------------------------------


class MockValidProvider:
    def __init__(self, response_text: str):
        self.response_text = response_text

    def generate_explanation(
        self,
        risk_level: RiskLevel,
        risk_score: float,
        reason: str,
        alert_recipient: AlertRecipient,
        follow_up_action: Optional[str] = None,
    ) -> str:
        return self.response_text


def test_provider_success_returns_validated_explanation():
    valid_text = (
        "The patient check-in has been assessed as Low risk. Routine follow-up "
        "is suggested to track symptom progress."
    )
    provider = MockValidProvider(valid_text)
    service = ExplanationService(provider=provider)
    assessment = _make_assessment(RiskLevel.LOW, 15)

    result = service.generate_explanation(assessment, "Routine monitoring.")
    assert result == valid_text


# --- Provider failure and failure isolation tests ----------------------------


class MockFailingProvider:
    def generate_explanation(self, *args, **kwargs) -> str:
        raise RuntimeError("Provider connection failed or timed out.")


def test_provider_exception_falls_back_safely():
    service = ExplanationService(provider=MockFailingProvider())
    assessment = _make_assessment(RiskLevel.MEDIUM, 45)
    action = "Care-team review."

    result = service.generate_explanation(assessment, action)
    assert result == generate_fallback_explanation(RiskLevel.MEDIUM, 45.0, action)


class MockEmptyProvider:
    def __init__(self, output: str):
        self.output = output

    def generate_explanation(self, *args, **kwargs) -> str:
        return self.output


@pytest.mark.parametrize("empty_output", ["", "   ", "\n\t  "])
def test_empty_or_whitespace_provider_output_falls_back(empty_output):
    service = ExplanationService(provider=MockEmptyProvider(empty_output))
    assessment = _make_assessment(RiskLevel.LOW, 20)
    action = "Continue monitoring."

    result = service.generate_explanation(assessment, action)
    assert result == generate_fallback_explanation(RiskLevel.LOW, 20.0, action)


def test_excessively_long_output_falls_back():
    long_text = "The assessment is Low risk. " + ("Extra context. " * 100)
    assert len(long_text) > MAX_EXPLANATION_LENGTH
    service = ExplanationService(provider=MockEmptyProvider(long_text))
    assessment = _make_assessment(RiskLevel.LOW, 15)

    result = service.generate_explanation(assessment, "Routine.")
    assert result == generate_fallback_explanation(RiskLevel.LOW, 15.0, "Routine.")


# --- Contradiction validation tests ------------------------------------------


@pytest.mark.parametrize(
    "expected_level, contradictory_text",
    [
        (RiskLevel.LOW, "The patient has a Medium risk status based on recent symptoms."),
        (RiskLevel.LOW, "This indicates High risk for the patient."),
        (RiskLevel.MEDIUM, "The assessment indicates Low risk overall."),
        (RiskLevel.MEDIUM, "This represents a High risk situation."),
        (RiskLevel.HIGH, "The patient check-in is classified as Low risk."),
        (RiskLevel.HIGH, "This corresponds to Medium risk."),
    ],
)
def test_contradictory_risk_level_falls_back(expected_level, contradictory_text):
    service = ExplanationService(provider=MockEmptyProvider(contradictory_text))
    assessment = _make_assessment(expected_level, 50)
    action = "Follow up."

    result = service.generate_explanation(assessment, action)
    assert result == generate_fallback_explanation(expected_level, 50.0, action)


# --- Safety validation tests: rejection of forbidden clinical phrases --------


@pytest.mark.parametrize(
    "forbidden_phrase",
    FORBIDDEN_EXPLANATION_PHRASES,
)
def test_forbidden_clinical_phrases_are_rejected_and_fall_back(forbidden_phrase):
    candidate = f"The patient is Low risk but is {forbidden_phrase}."
    assert not validate_explanation(candidate, RiskLevel.LOW)

    service = ExplanationService(provider=MockEmptyProvider(candidate))
    assessment = _make_assessment(RiskLevel.LOW, 15)
    action = "Routine monitoring."

    result = service.generate_explanation(assessment, action)
    assert result == generate_fallback_explanation(RiskLevel.LOW, 15.0, action)


# --- Deterministic integrity & observational immutability -------------------


def test_explanation_service_does_not_mutate_assessment_or_action():
    original_assessment = _make_assessment(RiskLevel.MEDIUM, 40, "Original reason", AlertRecipient.CARE_TEAM)
    assessment = _make_assessment(RiskLevel.MEDIUM, 40, "Original reason", AlertRecipient.CARE_TEAM)
    action = "Care-team review."

    explanation = generate_explanation(assessment, action)
    assert isinstance(explanation, str)
    assert len(explanation) > 0

    # Verify assessment fields remain completely untouched
    assert assessment.risk_score == original_assessment.risk_score
    assert assessment.risk_level == original_assessment.risk_level
    assert assessment.reason == original_assessment.reason
    assert assessment.alert_recipient == original_assessment.alert_recipient
    assert action == "Care-team review."


def test_repeated_calls_to_generate_explanation_are_stable():
    assessment = _make_assessment(RiskLevel.HIGH, 75, "Severe symptoms", AlertRecipient.PHYSICIAN)
    action = "Prompt physician review."
    results = [generate_explanation(assessment, action) for _ in range(10)]
    assert len(set(results)) == 1


# --- Static safety check: no unmocked network or external I/O imports --------


def test_explanation_module_contains_no_network_or_io_imports():
    source = inspect.getsource(explanation_service)
    forbidden_tokens = [
        "requests",
        "httpx",
        "urllib",
        "socket",
        "http.client",
        "boto3",
        "openai",
        "anthropic",
        "psycopg2",
        "sqlalchemy",
        "smtplib",
        "subprocess",
    ]
    lowered = source.lower()
    for token in forbidden_tokens:
        assert token not in lowered
