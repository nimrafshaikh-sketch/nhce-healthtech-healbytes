"""Validation tests for the AI Engine response contract (Phase 6: matches
`backend/apps/checkins/ai_client.py`'s `_parse_response` exactly)."""

import pytest
from pydantic import ValidationError

from app.schemas.response import AIAnalysisResponse
from tests.factories import valid_response_payload


def test_valid_response_is_accepted():
    response = AIAnalysisResponse.model_validate(valid_response_payload())
    assert response.riskLevel == "medium"
    assert response.riskScore == 0.425


def test_missing_required_field_is_rejected():
    payload = valid_response_payload()
    del payload["riskLevel"]
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


@pytest.mark.parametrize("invalid_level", ["Low", "URGENT", ""])
def test_invalid_risk_level_is_rejected(invalid_level):
    payload = valid_response_payload()
    payload["riskLevel"] = invalid_level
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


@pytest.mark.parametrize("invalid_score", [-0.1, 1.1, "high"])
def test_invalid_risk_score_is_rejected(invalid_score):
    payload = valid_response_payload()
    payload["riskScore"] = invalid_score
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_risk_score_as_bool_is_rejected():
    payload = valid_response_payload()
    payload["riskScore"] = True
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_risk_score_boundaries_are_accepted():
    for boundary in (0.0, 1.0):
        payload = valid_response_payload()
        payload["riskScore"] = boundary
        response = AIAnalysisResponse.model_validate(payload)
        assert response.riskScore == boundary


def test_invalid_notification_recipient_is_rejected():
    payload = valid_response_payload()
    payload["notificationRecipient"] = "family_member"
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_notification_recipient_none_is_valid():
    payload = valid_response_payload()
    payload["notificationRecipient"] = "none"
    response = AIAnalysisResponse.model_validate(payload)
    assert response.notificationRecipient == "none"


def test_empty_reason_is_rejected():
    payload = valid_response_payload()
    payload["reason"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_empty_recommended_action_is_rejected():
    payload = valid_response_payload()
    payload["recommendedAction"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_unexpected_field_is_rejected():
    payload = valid_response_payload()
    payload["explanation"] = "not part of the agreed contract"
    with pytest.raises(ValidationError):
        AIAnalysisResponse.model_validate(payload)


def test_serialized_output_uses_exact_wire_keys():
    response = AIAnalysisResponse.model_validate(valid_response_payload())
    dumped = response.model_dump(mode="json")
    assert set(dumped.keys()) == {
        "riskLevel",
        "riskScore",
        "reason",
        "recommendedAction",
        "notificationRecipient",
    }
