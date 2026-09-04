"""Builds the Receptionist Agent's `ToolRegistry`.

Role-specific tool registry for front-desk and clinic coordination tasks.
"""

from app.agents.tools.base import ToolRegistry
from app.agents.tools.receptionist_tools import (
    generate_invitation_code,
    list_appointments,
    list_available_doctors,
    register_patient,
    schedule_appointment,
    search_patient_registry,
    update_appointment_status,
)


def build_receptionist_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(list_appointments)
    registry.register(search_patient_registry)
    registry.register(register_patient)
    registry.register(generate_invitation_code)
    registry.register(schedule_appointment)
    registry.register(update_appointment_status)
    registry.register(list_available_doctors)
    return registry

