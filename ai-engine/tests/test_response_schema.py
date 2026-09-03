"""Validation tests for the AI Engine response contract."""

import pytest
from pydantic import ValidationError

from app.schemas.response import AIAnalysisResponse
from tests.factories import valid_response_payload


def test_valid_response_is_accepted():
    response = AIAnalysisResponse.model_validate(valid_response_payload())
    assert response.risk_level == "Medium"


def test_missing_required_field_is_rejected():
    payload = valid_response_payload()
    del payload["risk_level"]
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


@pytest.mark.parametrize("invalid_level", ["low", "URGENT", ""])
def test_invalid_risk_level_is_rejected(invalid_level):
    payload = valid_response_payload()
    payload["risk_level"] = invalid_level
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


@pytest.mark.parametrize("invalid_score", [-1, 100.1, "high"])
def test_invalid_risk_score_is_rejected(invalid_score):
    payload = valid_response_payload()
    payload["risk_score"] = invalid_score
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_invalid_alert_recipient_is_rejected():
    payload = valid_response_payload()
    payload["alert_recipient"] = "family_member"
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


# --- Response contract consistency (correction pass) ------------------------


def test_alert_recipient_is_required():
    payload = valid_response_payload()
    del payload["alert_recipient"]
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_alert_recipient_none_is_valid():
    payload = valid_response_payload()
    payload["alert_recipient"] = "none"
    response = AIAnalysisResponse.model_validate(payload)
    assert response.alert_recipient == "none"


def test_follow_up_action_may_be_null():
    payload = valid_response_payload()
    payload["follow_up_action"] = None
    response = AIAnalysisResponse.model_validate(payload)
    assert response.follow_up_action is None
    # The field is always present in the serialized output, even when null.
    assert "follow_up_action" in response.model_dump()


def test_follow_up_action_omitted_defaults_to_null_but_present():
    payload = valid_response_payload()
    del payload["follow_up_action"]
    response = AIAnalysisResponse.model_validate(payload)
    assert response.follow_up_action is None
    assert "follow_up_action" in response.model_dump()


def test_follow_up_action_with_valid_text_is_accepted():
    payload = valid_response_payload()
    payload["follow_up_action"] = "Schedule a follow-up call within 24 hours."
    response = AIAnalysisResponse.model_validate(payload)
    assert response.follow_up_action == "Schedule a follow-up call within 24 hours."


def test_empty_follow_up_action_is_rejected():
    payload = valid_response_payload()
    payload["follow_up_action"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


# --- Non-empty string validation (correction pass) ---------------------------


def test_empty_request_id_is_rejected():
    payload = valid_response_payload()
    payload["request_id"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_empty_reason_is_rejected():
    payload = valid_response_payload()
    payload["reason"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_empty_model_version_is_rejected():
    payload = valid_response_payload()
    payload["model_version"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


# --- Strict primitive types: reject coercion, not just wrong values ---------


def test_risk_score_as_numeric_string_is_rejected():
    payload = valid_response_payload()
    payload["risk_score"] = "42.5"
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_risk_score_as_bool_is_rejected():
    payload = valid_response_payload()
    payload["risk_score"] = True
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


# --- Phase 5 explanation field validation ------------------------------------


def test_explanation_may_be_null():
    payload = valid_response_payload()
    payload["explanation"] = None
    response = AIAnalysisResponse.model_validate(payload)
    assert response.explanation is None
    assert "explanation" in response.model_dump()


def test_explanation_omitted_defaults_to_null_but_present():
    payload = valid_response_payload()
    if "explanation" in payload:
        del payload["explanation"]
    response = AIAnalysisResponse.model_validate(payload)
    assert response.explanation is None
    assert "explanation" in response.model_dump()


def test_explanation_with_valid_text_is_accepted():
    payload = valid_response_payload()
    payload["explanation"] = "The assessment indicates Medium risk."
    response = AIAnalysisResponse.model_validate(payload)
    assert response.explanation == "The assessment indicates Medium risk."


def test_empty_explanation_is_rejected():
    payload = valid_response_payload()
    payload["explanation"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)
