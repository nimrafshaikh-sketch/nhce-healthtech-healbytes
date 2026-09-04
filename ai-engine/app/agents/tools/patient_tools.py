"""Proof-of-concept tool: read-only basic patient info via the existing backend.

Demonstrates the full Phase 1 flow end-to-end: Gemini selects this tool ->
the registry validates and executes it -> it calls the existing,
already-authorized `GET /api/patients/{id}/` endpoint on the Django
backend -> the result goes back to Gemini for its final natural-language
reply. No new backend code, no database access, and no bypass of existing
auth/RBAC - the caller's own bearer token decides whether the call
succeeds, exactly as it would for the real frontend.

This was the only tool registered in Phase 1 (one read-only
proof-of-concept tool, per that phase's scope). Phase 2 reuses it
unchanged as one of the Doctor Agent's tools (see
`app/agents/tools/doctor_tools.py` and `doctor_registry.py`) rather than
duplicating it.
"""

from __future__ import annotations

from typing import Any

from app.agents.backend_client import BackendClient
from app.agents.tools.base import Tool, ToolContext

# Least privilege at every layer, not only the backend's: even though the
# backend's PatientSerializer includes clinical/contact fields the caller
# may well be authorized to see elsewhere, this tool only ever forwards a
# minimal, non-clinical subset to Gemini.
_ALLOWED_FIELDS = ("id", "full_name", "date_of_birth", "gender", "phone_number", "is_active")


def _get_patient_basic_info(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    patient_id = arguments["patient_id"]
    client = BackendClient()
    patient = client.get(f"/api/patients/{patient_id}/", bearer_token=context.bearer_token)
    return {field: patient.get(field) for field in _ALLOWED_FIELDS if field in patient}


get_patient_basic_info = Tool(
    name="get_patient_basic_info",
    description=(
        "Look up basic, non-clinical identifying information for one patient "
        "(name, date of birth, gender, phone number, active status) by patient "
        "ID. Only returns data the requesting user is already authorized to "
        "see via the existing backend; never includes medical notes or "
        "caretaker contact details."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "patient_id": {
                "type": "string",
                "description": "The ID of the patient to look up, as a string.",
            },
        },
        "required": ["patient_id"],
    },
    handler=_get_patient_basic_info,
)
