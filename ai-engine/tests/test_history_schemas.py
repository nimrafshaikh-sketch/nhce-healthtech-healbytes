"""Validation tests for the Phase 2 patient-history request/response contract."""

import pytest
from pydantic import ValidationError

from app.history.schemas import PatientHistoryRequest
from tests.factories import valid_history_request_payload


def test_valid_history_request_is_accepted():
    request = PatientHistoryRequest.model_validate(valid_history_request_payload())
    assert request.patient_id == "1"
    assert len(request.checkins) == 2


def test_empty_history_lists_are_valid():
    payload = valid_history_request_payload()
    payload["checkins"] = []
    payload["medications"] = []
    payload["lab_tests"] = []
    payload["appointments"] = []

    request = PatientHistoryRequest.model_validate(payload)
    assert request.checkins == []
    assert request.medications == []
    assert request.lab_tests == []
    assert request.appointments == []


def test_missing_required_field_is_rejected():
    payload = valid_history_request_payload()
    del payload["patient_id"]
    with pytest.raises(ValidationError):
        PatientHistoryRequest.model_validate(payload)


def test_unknown_field_is_rejected():
    payload = valid_history_request_payload()
    payload["unexpected_field"] = "nope"
    with pytest.raises(ValidationError):
        PatientHistoryRequest.model_validate(payload)


def test_invalid_checkin_pain_level_is_rejected():
    payload = valid_history_request_payload()
    payload["checkins"][0]["pain_level"] = 11
    with pytest.raises(ValidationError):
        PatientHistoryRequest.model_validate(payload)


def test_invalid_medication_frequency_enum_is_rejected():
    payload = valid_history_request_payload()
    payload["medications"][0]["frequency"] = "hourly"
    with pytest.raises(ValidationError):
        PatientHistoryRequest.model_validate(payload)


def test_invalid_lab_test_name_enum_is_rejected():
    payload = valid_history_request_payload()
    payload["lab_tests"][0]["test_name"] = "MRI"
    with pytest.raises(ValidationError):
        PatientHistoryRequest.model_validate(payload)


def test_invalid_appointment_status_enum_is_rejected():
    payload = valid_history_request_payload()
    payload["appointments"][0]["status"] = "postponed"
    with pytest.raises(ValidationError):
        PatientHistoryRequest.model_validate(payload)


def test_malformed_timestamp_is_rejected():
    payload = valid_history_request_payload()
    payload["as_of"] = "not-a-timestamp"
    with pytest.raises(ValidationError):
        PatientHistoryRequest.model_validate(payload)


# --- medication_reminder_logs (additive, Phase 2 extension) -------------------


def test_payload_without_medication_reminder_logs_field_is_still_valid():
    """Backward compatibility: every payload accepted before this field
    existed must still be accepted, defaulting to an empty list."""
    payload = valid_history_request_payload()
    assert "medication_reminder_logs" not in payload  # factory predates this field
    request = PatientHistoryRequest.model_validate(payload)
    assert request.medication_reminder_logs == []


def test_valid_medication_reminder_log_is_accepted():
    payload = valid_history_request_payload()
    payload["medication_reminder_logs"] = [
        {
            "id": 1,
            "medication_id": 10,
            "scheduled_for": "2026-09-01T08:00:00+00:00",
            "sent_at": "2026-09-01T08:00:05+00:00",
            "acknowledged_at": "2026-09-01T08:10:00+00:00",
        }
    ]
    request = PatientHistoryRequest.model_validate(payload)
    assert len(request.medication_reminder_logs) == 1
    assert request.medication_reminder_logs[0].acknowledged_at is not None


def test_medication_reminder_log_missing_sent_at_is_rejected():
    payload = valid_history_request_payload()
    payload["medication_reminder_logs"] = [
        {"id": 1, "medication_id": 10, "scheduled_for": "2026-09-01T08:00:00+00:00"}
    ]
    with pytest.raises(ValidationError):
        PatientHistoryRequest.model_validate(payload)


def test_medication_reminder_log_unknown_field_is_rejected():
    payload = valid_history_request_payload()
    payload["medication_reminder_logs"] = [
        {
            "id": 1,
            "medication_id": 10,
            "scheduled_for": "2026-09-01T08:00:00+00:00",
            "sent_at": "2026-09-01T08:00:05+00:00",
            "unexpected": "nope",
        }
    ]
    with pytest.raises(ValidationError):
        PatientHistoryRequest.model_validate(payload)
