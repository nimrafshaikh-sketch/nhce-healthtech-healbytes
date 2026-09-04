"""Tests for the Phase 6 deterministic rule-based risk engine (pain_level +
symptom count, matching the agreed backend wire contract)."""

import pytest

from app.analysis.risk_engine import (
    MODEL_VERSION,
    assess,
    classify_risk_level,
    compute_risk_score,
    map_notification_recipient,
    score_pain_level,
    score_symptom_count,
)
from app.schemas.common import NotificationRecipient, RiskLevel
from app.schemas.request import AIAnalysisRequest
from tests.factories import valid_request_payload

# --- Individual factor scoring ------------------------------------------------


@pytest.mark.parametrize(
    "pain_level, expected",
    [(None, 0), (0, 0), (2, 0), (3, 25), (5, 25), (6, 50), (8, 50), (9, 75), (10, 75)],
)
def test_score_pain_level(pain_level, expected):
    assert score_pain_level(pain_level) == expected


@pytest.mark.parametrize(
    "count, expected",
    [(0, 0), (1, 0), (2, 10), (3, 10), (4, 25), (10, 25)],
)
def test_score_symptom_count(count, expected):
    assert score_symptom_count(count) == expected


# --- Score composition & clamping --------------------------------------------


def test_compute_risk_score_is_clamped_to_100():
    score = compute_risk_score(10, 5)
    assert score <= 100
    assert score == 100  # 75 + 25 = 100


def test_compute_risk_score_minimum_is_not_negative():
    score = compute_risk_score(None, 0)
    assert score == 0


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


# --- Notification recipient placeholder mapping -------------------------------


@pytest.mark.parametrize(
    "risk_level, expected_recipient",
    [
        (RiskLevel.LOW, NotificationRecipient.NONE),
        (RiskLevel.MEDIUM, NotificationRecipient.CARETAKER),
        (RiskLevel.HIGH, NotificationRecipient.DOCTOR),
    ],
)
def test_map_notification_recipient(risk_level, expected_recipient):
    assert map_notification_recipient(risk_level) == expected_recipient


def test_both_is_never_produced_by_the_deterministic_mapping():
    for level in RiskLevel:
        assert map_notification_recipient(level) != NotificationRecipient.BOTH


# --- End-to-end assess(): factor combinations ---------------------------------


def test_low_risk_combination():
    payload = valid_request_payload()
    payload["symptoms"] = ["mild headache"]
    payload["pain_level"] = 2
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert result.risk_score == 0
    assert result.risk_level == RiskLevel.LOW
    assert result.notification_recipient == NotificationRecipient.NONE


def test_medium_risk_combination():
    payload = valid_request_payload()
    payload["symptoms"] = ["headache", "fatigue"]
    payload["pain_level"] = 5
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert result.risk_score == 35  # 25 (pain) + 10 (2 symptoms)
    assert result.risk_level == RiskLevel.MEDIUM
    assert result.notification_recipient == NotificationRecipient.CARETAKER


def test_high_risk_combination():
    payload = valid_request_payload()
    payload["symptoms"] = ["chest pain", "shortness of breath", "dizziness", "fatigue"]
    payload["pain_level"] = 9
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert result.risk_score == 100  # 75 (pain) + 25 (4 symptoms)
    assert result.risk_level == RiskLevel.HIGH
    assert result.notification_recipient == NotificationRecipient.DOCTOR


# --- Determinism ---------------------------------------------------------------


def test_assess_is_deterministic_across_repeated_calls():
    payload = valid_request_payload()

    first = assess(AIAnalysisRequest.model_validate(payload))
    second = assess(AIAnalysisRequest.model_validate(payload))

    assert first == second  # RiskAssessment is a frozen dataclass: full equality


# --- Reason text reflects actual contributing factors -------------------------


def test_reason_mentions_pain_level_when_reported():
    payload = valid_request_payload()
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert result.reason
    assert "pain level" in result.reason.lower()


def test_reason_reflects_missing_pain_level():
    payload = valid_request_payload()
    payload["pain_level"] = None
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert "no pain level was reported" in result.reason.lower()


def test_reason_flags_mood_vitals_notes_as_unscored():
    payload = valid_request_payload()
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)
    lowered = result.reason.lower()

    assert "mood" in lowered
    assert "vitals" in lowered
    assert "notes" in lowered
    assert "not yet scored" in lowered


def test_reason_omits_unscored_note_when_fields_absent():
    payload = valid_request_payload()
    payload["mood"] = None
    payload["vitals"] = {}
    payload["notes"] = None
    request = AIAnalysisRequest.model_validate(payload)

    result = assess(request)

    assert "not yet scored" not in result.reason.lower()


def test_empty_mood_string_is_treated_as_unspecified_not_a_value():
    # An empty string ("" from Django's blank=True CharField default) must
    # be treated the same as a missing mood, not scored or flagged as a
    # provided value, and must not affect the score.
    payload = valid_request_payload()
    payload["mood"] = ""
    payload["vitals"] = {}
    payload["notes"] = None
    request_empty = AIAnalysisRequest.model_validate(payload)

    payload_null = valid_request_payload()
    payload_null["mood"] = None
    payload_null["vitals"] = {}
    payload_null["notes"] = None
    request_null = AIAnalysisRequest.model_validate(payload_null)

    result_empty = assess(request_empty)
    result_null = assess(request_null)

    assert "not yet scored" not in result_empty.reason.lower()
    assert result_empty.risk_score == result_null.risk_score
    assert result_empty.reason == result_null.reason


# --- Model version -------------------------------------------------------------


def test_model_version_constant_is_rule_engine_v6():
    assert MODEL_VERSION == "rule-engine-v6"
