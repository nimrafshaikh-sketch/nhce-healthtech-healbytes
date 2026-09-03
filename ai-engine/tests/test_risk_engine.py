"""Tests for the Phase 1 deterministic rule-based risk engine."""

import pytest

from app.analysis.risk_engine import (
    MODEL_VERSION,
    assess,
    classify_risk_level,
    compute_risk_score,
    map_alert_recipient,
    score_duration,
    score_medical_history,
    score_severity,
    score_symptom_count,
)
from app.schemas.common import AlertRecipient, DurationUnit, RiskLevel, SeverityLevel
from app.schemas.request import AIAnalysisRequest, Duration, MedicalContext
from tests.factories import valid_request_payload


# --- Individual factor scoring ------------------------------------------------


@pytest.mark.parametrize(
    "severity, expected",
    [
        (SeverityLevel.MILD, 15),
        (SeverityLevel.MODERATE, 40),
        (SeverityLevel.SEVERE, 70),
    ],
)
def test_score_severity(severity, expected):
    assert score_severity(severity) == expected


@pytest.mark.parametrize(
    "value, unit, expected",
    [
        (24, DurationUnit.HOURS, 0),
        (1, DurationUnit.DAYS, 0),  # 24h, still in the 0-24h bucket
        (2, DurationUnit.DAYS, 10),  # 48h
        (3, DurationUnit.DAYS, 10),  # 72h, upper edge of the 10-point bucket
        (4, DurationUnit.DAYS, 20),  # 96h
        (1, DurationUnit.WEEKS, 20),  # 168h, upper edge of the 20-point bucket
        (2, DurationUnit.WEEKS, 30),  # 336h
    ],
)
def test_score_duration(value, unit, expected):
    assert score_duration(Duration(value=value, unit=unit)) == expected


@pytest.mark.parametrize(
    "count, expected",
    [(1, 0), (2, 10), (3, 10), (4, 20), (10, 20)],
)
def test_score_symptom_count(count, expected):
    assert score_symptom_count(count) == expected


def test_score_medical_history_present():
    context = MedicalContext(medical_history=["hypertension"])
    assert score_medical_history(context) == 5


def test_score_medical_history_absent():
    context = MedicalContext(medical_history=[])
    assert score_medical_history(context) == 0


# --- Score composition & clamping --------------------------------------------


def test_compute_risk_score_is_clamped_to_100():
    context = MedicalContext(medical_history=["hypertension"])
    duration = Duration(value=2, unit=DurationUnit.WEEKS)
    score = compute_risk_score(SeverityLevel.SEVERE, duration, 5, context)
    assert score <= 100
    assert score == 100  # 70 + 30 + 20 + 5 = 125, clamped to 100


def test_compute_risk_score_minimum_is_not_negative():
    context = MedicalContext(medical_history=[])
    duration = Duration(value=1, unit=DurationUnit.HOURS)
    score = compute_risk_score(SeverityLevel.MILD, duration, 1, context)
    assert score >= 0
    assert score == 15


# --- Classification boundaries -------------------------------------------------


@pytest.mark.parametrize(
    "score, expected_level",
    [
        (0, RiskLevel.LOW),
        (34, RiskLevel.LOW),
        (35, RiskLevel.MEDIUM),
        (69, RiskLevel.MEDIUM),
        (70, RiskLevel.HIGH),
        (100, RiskLevel.HIGH),
    ],
)
def test_classify_risk_level_boundaries(score, expected_level):
    assert classify_risk_level(score) == expected_level


# --- Alert recipient placeholder mapping --------------------------------------


@pytest.mark.parametrize(
    "risk_level, expected_recipient",
    [
        (RiskLevel.LOW, AlertRecipient.NONE),
        (RiskLevel.MEDIUM, AlertRecipient.CARE_TEAM),
        (RiskLevel.HIGH, AlertRecipient.PHYSICIAN),
    ],
)
def test_map_alert_recipient(risk_level, expected_recipient):
    assert map_alert_recipient(risk_level) == expected_recipient


def test_emergency_services_is_never_produced():
    for level in RiskLevel:
        assert map_alert_recipient(level) != AlertRecipient.EMERGENCY_SERVICES


# --- End-to-end assess(): factor combinations ---------------------------------


def test_low_risk_combination():
    payload = valid_request_payload()
    payload["medical_context"]["medical_history"] = []
    payload["check_in"] = {
        "symptoms": ["mild headache"],
        "severity": "mild",
        "duration": {"value": 2, "unit": "hours"},
    }
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert result.risk_score == 15
    assert result.risk_level == RiskLevel.LOW
    assert result.alert_recipient == AlertRecipient.NONE


def test_medium_risk_combination():
    payload = valid_request_payload()
    payload["medical_context"]["medical_history"] = []
    payload["check_in"] = {
        "symptoms": ["headache", "fatigue"],
        "severity": "moderate",
        "duration": {"value": 2, "unit": "days"},
    }
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert result.risk_score == 60
    assert result.risk_level == RiskLevel.MEDIUM
    assert result.alert_recipient == AlertRecipient.CARE_TEAM


def test_high_risk_combination():
    payload = valid_request_payload()
    payload["medical_context"]["medical_history"] = ["asthma"]
    payload["check_in"] = {
        "symptoms": ["chest pain", "shortness of breath", "dizziness", "fatigue"],
        "severity": "severe",
        "duration": {"value": 2, "unit": "weeks"},
    }
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert result.risk_score == 100
    assert result.risk_level == RiskLevel.HIGH
    assert result.alert_recipient == AlertRecipient.PHYSICIAN


# --- Determinism ---------------------------------------------------------------


def test_assess_is_deterministic_across_repeated_calls():
    payload = valid_request_payload()

    first = assess(AIAnalysisRequest.model_validate(payload))
    second = assess(AIAnalysisRequest.model_validate(payload))

    assert first == second  # RiskAssessment is a frozen dataclass: full equality


def test_assess_is_deterministic_for_score_level_and_reason_independently():
    payload = valid_request_payload()

    results = [assess(AIAnalysisRequest.model_validate(payload)) for _ in range(5)]

    assert len({r.risk_score for r in results}) == 1
    assert len({r.risk_level for r in results}) == 1
    assert len({r.reason for r in results}) == 1


# --- Reason text reflects actual contributing factors -------------------------


def test_reason_is_non_empty_and_mentions_severity():
    payload = valid_request_payload()
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert result.reason
    assert "severity" in result.reason.lower()


def test_reason_mentions_duration_when_it_contributes():
    payload = valid_request_payload()
    payload["check_in"]["duration"] = {"value": 2, "unit": "weeks"}
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert "duration" in result.reason.lower()


def test_reason_mentions_symptom_count_when_it_contributes():
    payload = valid_request_payload()
    payload["check_in"]["symptoms"] = ["a", "b", "c", "d"]
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert "symptoms" in result.reason.lower()


def test_reason_mentions_medical_history_when_it_contributes():
    payload = valid_request_payload()
    payload["medical_context"]["medical_history"] = ["hypertension"]
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert "medical history" in result.reason.lower()


# --- Fields explicitly excluded from Phase 1 scoring ---------------------------


def test_medication_adherence_does_not_affect_score():
    with_adherence_payload = valid_request_payload()
    without_adherence_payload = valid_request_payload()
    without_adherence_payload["medical_context"]["medication_adherence"] = []

    with_adherence = assess(AIAnalysisRequest.model_validate(with_adherence_payload))
    without_adherence = assess(AIAnalysisRequest.model_validate(without_adherence_payload))

    assert with_adherence.risk_score == without_adherence.risk_score
    assert with_adherence.risk_level == without_adherence.risk_level


def test_historical_checkins_do_not_affect_score():
    with_history_payload = valid_request_payload()
    without_history_payload = valid_request_payload()
    without_history_payload["historical_context"]["previous_checkins"] = []

    with_history = assess(AIAnalysisRequest.model_validate(with_history_payload))
    without_history = assess(AIAnalysisRequest.model_validate(without_history_payload))

    assert with_history.risk_score == without_history.risk_score
    assert with_history.risk_level == without_history.risk_level


# --- Model version -------------------------------------------------------------


def test_model_version_constant_is_rule_engine_v4():
    # Bumped in Phase 4 ("rule-engine-v1" -> "v2" -> "v3" -> "v4" here):
    # the response's model_version identifies the composed baseline + trend +
    # medication-adherence + follow-up recommendation pipeline (see
    # app/analysis/risk_assessor.py and app/analysis/follow_up_recommender.py),
    # not just this module's baseline scorer.
    assert MODEL_VERSION == "rule-engine-v4"
