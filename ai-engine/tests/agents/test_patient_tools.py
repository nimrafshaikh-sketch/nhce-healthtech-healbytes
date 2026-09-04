"""Tests for the one Phase 1 proof-of-concept tool: `get_patient_basic_info`.

The backend HTTP call is mocked (via `BackendClient.get`) - these tests
verify the tool's own contract: least-privilege field filtering and
argument handling, not the real Django backend.
"""

from unittest.mock import patch

from app.agents.tools.base import ToolContext
from app.agents.tools.patient_tools import get_patient_basic_info


@patch("app.agents.tools.patient_tools.BackendClient")
def test_returns_only_allowed_fields(mock_backend_client_cls):
    mock_backend_client_cls.return_value.get.return_value = {
        "id": 7,
        "full_name": "Jane Doe",
        "date_of_birth": "1990-01-01",
        "gender": "female",
        "phone_number": "555-0100",
        "is_active": True,
        "medical_notes": "sensitive clinical content",
        "caretaker_phone_number": "555-0199",
    }

    result = get_patient_basic_info.handler(
        {"patient_id": "7"}, ToolContext(bearer_token="tok")
    )

    assert result == {
        "id": 7,
        "full_name": "Jane Doe",
        "date_of_birth": "1990-01-01",
        "gender": "female",
        "phone_number": "555-0100",
        "is_active": True,
    }
    assert "medical_notes" not in result
    assert "caretaker_phone_number" not in result


@patch("app.agents.tools.patient_tools.BackendClient")
def test_forwards_patient_id_and_bearer_token(mock_backend_client_cls):
    mock_backend_client_cls.return_value.get.return_value = {"id": 3}

    get_patient_basic_info.handler({"patient_id": "3"}, ToolContext(bearer_token="secret"))

    mock_backend_client_cls.return_value.get.assert_called_once_with(
        "/api/patients/3/", bearer_token="secret"
    )


def test_tool_declares_required_patient_id():
    schema = get_patient_basic_info.parameters_json_schema
    assert schema["required"] == ["patient_id"]
    assert "patient_id" in schema["properties"]
