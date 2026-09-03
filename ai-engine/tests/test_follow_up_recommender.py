"""Tests for the Phase 4 deterministic follow-up recommendation engine.

`recommend_follow_up` is pure and maps a `RiskLevel` to a care-coordination
`follow_up_action` string — no request, no network, no database, no LLM,
no I/O — tested in isolation here.
"""

import inspect

import pytest

from app.analysis import follow_up_recommender
from app.analysis.follow_up_recommender import (
    FOLLOW_UP_RECOMMENDATIONS,
    recommend_follow_up,
)
from app.analysis.risk_engine import classify_risk_level
from app.schemas.common import RiskLevel

# Forbidden clinical, diagnostic, treatment, medication change, or emergency claims
_FORBIDDEN_PHRASES = [
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


# --- Mapping -----------------------------------------------------------------


def test_low_risk_recommends_routine_monitoring():
    action = recommend_follow_up(RiskLevel.LOW)
    assert action == FOLLOW_UP_RECOMMENDATIONS[RiskLevel.LOW]
    assert "routine monitoring" in action.lower()
    assert "next scheduled check-in" in action.lower()


def test_medium_risk_recommends_care_team_review():
    action = recommend_follow_up(RiskLevel.MEDIUM)
    assert action == FOLLOW_UP_RECOMMENDATIONS[RiskLevel.MEDIUM]
    assert "care-team review" in action.lower()
    assert "closer follow-up" in action.lower()


def test_high_risk_recommends_physician_review():
    action = recommend_follow_up(RiskLevel.HIGH)
    assert action == FOLLOW_UP_RECOMMENDATIONS[RiskLevel.HIGH]
    assert "physician review" in action.lower()


# --- Determinism -------------------------------------------------------------


@pytest.mark.parametrize("risk_level", list(RiskLevel))
def test_recommendation_is_deterministic_for_identical_input(risk_level):
    first = recommend_follow_up(risk_level)
    second = recommend_follow_up(risk_level)
    assert first == second


@pytest.mark.parametrize("risk_level", list(RiskLevel))
def test_repeated_calls_are_stable(risk_level):
    results = [recommend_follow_up(risk_level) for _ in range(10)]
    assert len(set(results)) == 1


# --- Risk-score independence and threshold boundary behavior ------------------


@pytest.mark.parametrize(
    "score, expected_level",
    [
        (0, RiskLevel.LOW),
        (15, RiskLevel.LOW),
        (34, RiskLevel.LOW),
        (35, RiskLevel.MEDIUM),
        (50, RiskLevel.MEDIUM),
        (69, RiskLevel.MEDIUM),
        (70, RiskLevel.HIGH),
        (85, RiskLevel.HIGH),
        (100, RiskLevel.HIGH),
    ],
)
def test_follow_up_action_across_risk_score_boundaries(score, expected_level):
    level = classify_risk_level(score)
    assert level == expected_level
    action = recommend_follow_up(level)
    assert action == FOLLOW_UP_RECOMMENDATIONS[expected_level]


def test_different_scores_in_same_risk_band_yield_identical_action():
    # Scores 0, 15, 34 all classify as Low
    actions_low = {recommend_follow_up(classify_risk_level(s)) for s in (0, 15, 34)}
    assert len(actions_low) == 1

    # Scores 35, 50, 69 all classify as Medium
    actions_med = {recommend_follow_up(classify_risk_level(s)) for s in (35, 50, 69)}
    assert len(actions_med) == 1

    # Scores 70, 85, 100 all classify as High
    actions_high = {recommend_follow_up(classify_risk_level(s)) for s in (70, 85, 100)}
    assert len(actions_high) == 1


# --- Safety checks -----------------------------------------------------------


@pytest.mark.parametrize("risk_level", list(RiskLevel))
def test_recommendation_never_contains_forbidden_clinical_phrases(risk_level):
    action = recommend_follow_up(risk_level).lower()
    for phrase in _FORBIDDEN_PHRASES:
        assert phrase not in action


@pytest.mark.parametrize("risk_level", list(RiskLevel))
def test_recommendation_is_non_empty_string(risk_level):
    action = recommend_follow_up(risk_level)
    assert isinstance(action, str)
    assert len(action.strip()) > 0


def test_recommendation_does_not_mutate_enum():
    original_levels = list(RiskLevel)
    for level in original_levels:
        recommend_follow_up(level)
    assert list(RiskLevel) == original_levels


# --- Static check: No network / external I/O imports -------------------------


def test_module_source_contains_no_network_or_io_imports():
    source = inspect.getsource(follow_up_recommender)
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
    ]
    lowered = source.lower()
    for token in forbidden_tokens:
        assert token not in lowered
