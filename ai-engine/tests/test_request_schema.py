"""Validation tests for the AI Engine request contract (Phase 6: matches
`backend/apps/checkins/ai_client.py` exactly)."""

import pytest
from pydantic import ValidationError

from app.schemas.request import AIAnalysisRequest
from tests.factories import valid_request_payload


def test_valid_request_is_accepted():
    request = AIAnalysisRequest.model_validate(valid_request_payload())
    assert request.checkin_id == 1
    assert request.patient_id == 1
    assert request.pain_level == 4


def test_missing_required_field_is_rejected():
    payload = valid_request_payload()
    del payload["patient_id"]
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_checkin_id_as_non_int_is_rejected():
    payload = valid_request_payload()
    payload["checkin_id"] = "1"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_checkin_id_as_bool_is_rejected():
    payload = valid_request_payload()
    payload["checkin_id"] = True
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_unexpected_field_is_rejected():
    payload = valid_request_payload()
    payload["unexpected_field"] = "not allowed"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


# --- pain_level ----------------------------------------------------------


def test_pain_level_null_is_accepted_when_symptoms_present():
    payload = valid_request_payload()
    payload["pain_level"] = None
    request = AIAnalysisRequest.model_validate(payload)
    assert request.pain_level is None


def test_pain_level_omitted_defaults_to_null():
    payload = valid_request_payload()
    del payload["pain_level"]
    request = AIAnalysisRequest.model_validate(payload)
    assert request.pain_level is None


@pytest.mark.parametrize("value", [-1, 11])
def test_pain_level_out_of_assumed_0_to_10_range_is_rejected(value):
    payload = valid_request_payload()
    payload["pain_level"] = value
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_pain_level_as_numeric_string_is_rejected():
    payload = valid_request_payload()
    payload["pain_level"] = "4"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_pain_level_as_bool_is_rejected():
    payload = valid_request_payload()
    payload["pain_level"] = True
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


# --- symptoms --------------------------------------------------------------


def test_symptoms_omitted_defaults_to_empty_list():
    payload = valid_request_payload()
    del payload["symptoms"]
    request = AIAnalysisRequest.model_validate(payload)
    assert request.symptoms == []


def test_empty_symptom_string_is_rejected():
    payload = valid_request_payload()
    payload["symptoms"] = ["headache", ""]
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


# --- mood / vitals / notes: accepted, loosely typed -------------------------


def test_mood_vitals_notes_are_optional_and_accepted():
    payload = valid_request_payload()
    payload["mood"] = None
    payload["vitals"] = {"heart_rate": 100, "note": "irregular"}
    payload["notes"] = None
    request = AIAnalysisRequest.model_validate(payload)
    assert request.mood is None
    assert request.vitals == {"heart_rate": 100, "note": "irregular"}
    assert request.notes is None


def test_vitals_omitted_defaults_to_empty_dict():
    payload = valid_request_payload()
    del payload["vitals"]
    request = AIAnalysisRequest.model_validate(payload)
    assert request.vitals == {}


def test_empty_mood_string_is_accepted_as_unspecified():
    # Django's `mood = models.CharField(max_length=50, blank=True)` sends an
    # unset mood as "" (not null) — this must not be rejected.
    payload = valid_request_payload()
    payload["mood"] = ""
    request = AIAnalysisRequest.model_validate(payload)
    assert request.mood == ""


def test_normal_mood_value_is_accepted():
    payload = valid_request_payload()
    payload["mood"] = "distressed"
    request = AIAnalysisRequest.model_validate(payload)
    assert request.mood == "distressed"


# --- Insufficient-data safeguard: never fabricate a score --------------------


def test_empty_symptoms_and_null_pain_level_is_rejected():
    payload = valid_request_payload()
    payload["symptoms"] = []
    payload["pain_level"] = None
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_symptoms_alone_without_pain_level_is_sufficient():
    payload = valid_request_payload()
    payload["pain_level"] = None
    request = AIAnalysisRequest.model_validate(payload)
    assert request.pain_level is None
    assert request.symptoms


def test_pain_level_alone_without_symptoms_is_sufficient():
    payload = valid_request_payload()
    payload["symptoms"] = []
    request = AIAnalysisRequest.model_validate(payload)
    assert request.symptoms == []
    assert request.pain_level is not None
