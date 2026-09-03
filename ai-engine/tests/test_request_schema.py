"""Validation tests for the AI Engine request contract."""

import pytest
from pydantic import ValidationError

from app.schemas.request import AIAnalysisRequest
from tests.factories import valid_request_payload


def test_valid_request_is_accepted():
    request = AIAnalysisRequest.model_validate(valid_request_payload())
    assert request.patient_id == "patient-001"
    assert request.check_in.severity == "moderate"


def test_missing_required_field_is_rejected():
    payload = valid_request_payload()
    del payload["patient_id"]
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_invalid_data_type_is_rejected():
    payload = valid_request_payload()
    payload["timestamp"] = "not-a-timestamp"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_invalid_severity_enum_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["severity"] = "catastrophic"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_non_positive_duration_value_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["duration"]["value"] = 0
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_empty_symptoms_list_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["symptoms"] = []
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_nested_medication_adherence_status_is_validated():
    payload = valid_request_payload()
    payload["medical_context"]["medication_adherence"][0]["adherence_status"] = "invalid_status"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_unexpected_field_is_rejected():
    payload = valid_request_payload()
    payload["unexpected_field"] = "not allowed"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_request_without_optional_context_uses_defaults():
    payload = valid_request_payload()
    del payload["medical_context"]
    del payload["historical_context"]
    request = AIAnalysisRequest.model_validate(payload)
    assert request.medical_context.medical_history == []
    assert request.historical_context.previous_checkins == []


# --- Non-empty string validation (correction pass) ---------------------------


def test_empty_patient_id_is_rejected():
    payload = valid_request_payload()
    payload["patient_id"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_empty_request_id_is_rejected():
    payload = valid_request_payload()
    payload["request_id"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_empty_symptom_string_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["symptoms"] = ["headache", ""]
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_empty_medication_name_is_rejected():
    payload = valid_request_payload()
    payload["medical_context"]["medication_adherence"][0]["medication_name"] = ""
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_empty_medical_history_entry_is_rejected():
    payload = valid_request_payload()
    payload["medical_context"]["medical_history"] = [""]
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


# --- Strict primitive types: reject coercion, not just wrong values ---------


def test_duration_value_as_numeric_string_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["duration"]["value"] = "2"
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_duration_value_as_bool_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["duration"]["value"] = True
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_duration_value_as_float_is_rejected():
    payload = valid_request_payload()
    payload["check_in"]["duration"]["value"] = 2.0
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)


def test_patient_id_as_non_string_is_rejected():
    payload = valid_request_payload()
    payload["patient_id"] = 12345
    with pytest.raises(ValidationError):
        AIAnalysisRequest.model_validate(payload)
