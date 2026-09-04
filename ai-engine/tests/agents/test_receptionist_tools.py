"""Unit tests for Receptionist Agent tools."""

from unittest.mock import patch

import pytest

from app.agents.tools.base import ToolContext
from app.agents.tools.receptionist_tools import (
    _normalize_dob,
    generate_invitation_code,
    list_appointments,
    list_available_doctors,
    register_patient,
    schedule_appointment,
    search_patient_registry,
    update_appointment_status,
)


@pytest.fixture
def context():
    return ToolContext(bearer_token="receptionist-test-token")


def test_normalize_dob_formats():
    assert _normalize_dob("2005-08-21") == "2005-08-21"
    assert _normalize_dob("21 08 2005") == "2005-08-21"
    assert _normalize_dob("21-08-2005") == "2005-08-21"
    assert _normalize_dob("21/08/2005") == "2005-08-21"
    assert _normalize_dob("21 August 2005") == "2005-08-21"
    assert _normalize_dob("August 21, 2005") == "2005-08-21"


@patch("app.agents.tools.receptionist_tools.BackendClient")
def test_register_patient_success(mock_client_cls, context):
    mock_instance = mock_client_cls.return_value
    mock_instance.get.return_value = [{"id": 1, "first_name": "Sarah", "last_name": "Sharma"}]
    mock_instance.post.side_effect = [
        # 1st call: POST /api/patients/
        {"id": 40, "full_name": "Zynab Mathiya", "date_of_birth": "2005-08-21", "doctor": 1, "doctor_name": "Dr. Sarah Sharma"},
        # 2nd call: POST /api/invitations/generate/
        {"id": 15, "code": "INV-ZYNAB123456", "patient": 40, "expires_at": "2026-09-12T00:00:00Z"},
    ]

    res = register_patient.handler(
        {
            "full_name": "Zynab Mathiya",
            "date_of_birth": "21 08 2005",
            "gender": "female",
        },
        context,
    )

    assert res["status"] == "success"
    assert res["patient_id"] == 40
    assert res["full_name"] == "Zynab Mathiya"
    assert res["invitation_code"] == "INV-ZYNAB123456"
    assert "Zynab Mathiya" in res["message"]
    assert "INV-ZYNAB123456" in res["message"]


@patch("app.agents.tools.receptionist_tools.BackendClient")
def test_generate_invitation_code_success(mock_client_cls, context):
    mock_instance = mock_client_cls.return_value
    mock_instance.post.return_value = {
        "id": 16,
        "code": "INV-7848FBE02DAA",
        "patient": 40,
        "patient_name": "Zynab Mathiya",
        "expires_at": "2026-09-12T00:00:00Z",
    }

    res = generate_invitation_code.handler({"patient_id": "40"}, context)
    assert res["status"] == "success"
    assert res["invitation_code"] == "INV-7848FBE02DAA"
    assert "INV-7848FBE02DAA" in res["message"]


def test_register_patient_missing_required_fields(context):
    res_no_name = register_patient.handler({"date_of_birth": "2005-08-21"}, context)
    assert "error" in res_no_name

    res_no_dob = register_patient.handler({"full_name": "Zynab Mathiya"}, context)
    assert "error" in res_no_dob


@patch("app.agents.tools.receptionist_tools.BackendClient")
def test_list_appointments_success(mock_client_cls, context):
    mock_client_cls.return_value.get.return_value = [
        {
            "id": 10,
            "patient": 39,
            "patient_name": "Rahul Verma",
            "doctor": 1,
            "doctor_name": "Dr. Sarah Chen",
            "scheduled_at": "2026-09-08T10:30:00Z",
            "status": "SCHEDULED",
            "reason": "Follow-up",
            "notes": "",
        }
    ]

    res = list_appointments.handler({}, context)
    assert res["count"] == 1
    assert res["appointments"][0]["patient_name"] == "Rahul Verma"
    assert res["appointments"][0]["doctor_name"] == "Dr. Sarah Chen"


@patch("app.agents.tools.receptionist_tools.BackendClient")
def test_search_patient_registry_by_phone(mock_client_cls, context):
    mock_client_cls.return_value.get.return_value = [
        {"id": 39, "full_name": "Rahul Verma", "phone_number": "9876543210"}
    ]

    res = search_patient_registry.handler({"phone_number": "9876543210"}, context)
    assert res["count"] == 1
    assert res["patients"][0]["full_name"] == "Rahul Verma"


@patch("app.agents.tools.receptionist_tools.BackendClient")
def test_schedule_appointment_success(mock_client_cls, context):
    mock_client_cls.return_value.post.return_value = {
        "id": 12,
        "patient": 39,
        "doctor": 1,
        "scheduled_at": "2026-09-08T10:30:00Z",
        "status": "SCHEDULED",
        "reason": "Routine Checkup",
    }

    res = schedule_appointment.handler(
        {
            "patient_id": "39",
            "doctor_id": "1",
            "scheduled_at": "2026-09-08T10:30:00Z",
            "reason": "Routine Checkup",
        },
        context,
    )
    assert res["status"] == "success"
    assert res["appointment"]["id"] == 12


@patch("app.agents.tools.receptionist_tools.BackendClient")
def test_update_appointment_status_success(mock_client_cls, context):
    mock_client_cls.return_value.patch.return_value = {
        "id": 12,
        "status": "COMPLETED",
    }

    res = update_appointment_status.handler({"appointment_id": "12", "status": "COMPLETED"}, context)
    assert res["status"] == "success"
    assert res["appointment"]["status"] == "COMPLETED"


def test_update_appointment_status_invalid(context):
    res = update_appointment_status.handler({"appointment_id": "12", "status": "INVALID_STATUS"}, context)
    assert "error" in res


@patch("app.agents.tools.receptionist_tools.BackendClient")
def test_list_available_doctors(mock_client_cls, context):
    mock_client_cls.return_value.get.return_value = [
        {
            "id": 1,
            "first_name": "Sarah",
            "last_name": "Chen",
            "email": "doctor@healbytes.local",
            "specialization": "Cardiology",
            "phone_number": "9876543211",
        }
    ]

    res = list_available_doctors.handler({}, context)
    assert res["count"] == 1
    assert res["doctors"][0]["name"] == "Dr. Sarah Chen"
    assert res["doctors"][0]["specialization"] == "Cardiology"

