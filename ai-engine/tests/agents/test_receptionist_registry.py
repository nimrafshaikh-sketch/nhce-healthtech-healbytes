"""Tests for the Receptionist Agent's `ToolRegistry`."""

from app.agents.tools.receptionist_registry import build_receptionist_registry


def test_receptionist_registry_contains_all_expected_tools():
    registry = build_receptionist_registry()
    names = {decl["name"] for decl in registry.function_declarations()}
    assert names == {
        "list_appointments",
        "search_patient_registry",
        "register_patient",
        "generate_invitation_code",
        "schedule_appointment",
        "update_appointment_status",
        "list_available_doctors",
    }

