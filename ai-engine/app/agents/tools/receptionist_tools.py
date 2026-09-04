"""Receptionist Agent tool implementations.

These tools allow the Receptionist Agent to query and manage clinic
appointments, search patient records administratively, view doctor rosters,
and update appointment statuses using the caller's authorized bearer token.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from app.agents.backend_client import BackendClient
from app.agents.tools.base import Tool, ToolContext

logger = logging.getLogger(__name__)


def _normalize_dob(dob_raw: str) -> str:
    """Normalize various date formats (e.g. '21 08 2005', '21-08-2005', '21/08/2005') to YYYY-MM-DD."""
    if not dob_raw or not isinstance(dob_raw, str):
        return ""

    cleaned = dob_raw.strip()

    # Direct match for ISO format YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", cleaned):
        return cleaned

    spaced = re.sub(r"[,/.\-_]", " ", cleaned)
    spaced = re.sub(r"\s+", " ", spaced).strip()

    formats = [
        "%Y %m %d",
        "%d %m %Y",
        "%m %d %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%B %d %Y",
        "%b %d %Y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%Y/%m/%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(spaced, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
        try:
            return datetime.strptime(cleaned, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass

    # Regex fallback for 3 numeric parts:
    match = re.search(r"(\d{1,4})[\s\-\/\.]+(\d{1,2})[\s\-\/\.]+(\d{1,4})", cleaned)
    if match:
        p1, p2, p3 = match.groups()
        if len(p1) == 4:
            return f"{int(p1):04d}-{int(p2):02d}-{int(p3):02d}"
        elif len(p3) == 4:
            return f"{int(p3):04d}-{int(p2):02d}-{int(p1):02d}"

    return cleaned



# ---------------------------------------------------------------------------
# list_appointments
# ---------------------------------------------------------------------------

def _list_appointments(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    date = arguments.get("date", "")
    patient_id = arguments.get("patient_id", "")

    client = BackendClient()
    params: dict[str, Any] = {}
    if patient_id and str(patient_id).strip():
        params["patient"] = str(patient_id).strip()

    data = client.get("/api/appointments/", bearer_token=context.bearer_token, params=params if params else None)
    results = data if isinstance(data, list) else data.get("results", [])

    if date and date.strip():
        filter_date = date.strip()
        results = [
            appt for appt in results
            if str(appt.get("scheduled_at", "")).startswith(filter_date)
        ]

    formatted = []
    for appt in results:
        formatted.append({
            "id": appt.get("id"),
            "patient_id": appt.get("patient") if isinstance(appt.get("patient"), (int, str)) else (appt.get("patient", {}).get("id") if isinstance(appt.get("patient"), dict) else None),
            "patient_name": appt.get("patient_name") or (appt.get("patient", {}).get("full_name") if isinstance(appt.get("patient"), dict) else ""),
            "doctor_id": appt.get("doctor") if isinstance(appt.get("doctor"), (int, str)) else (appt.get("doctor", {}).get("id") if isinstance(appt.get("doctor"), dict) else None),
            "doctor_name": appt.get("doctor_name") or (appt.get("doctor", {}).get("full_name") if isinstance(appt.get("doctor"), dict) else ""),
            "scheduled_at": appt.get("scheduled_at"),
            "status": appt.get("status"),
            "reason": appt.get("reason"),
            "notes": appt.get("notes"),
        })

    return {
        "count": len(formatted),
        "appointments": formatted,
    }


list_appointments = Tool(
    name="list_appointments",
    description=(
        "Retrieve scheduled clinic appointments, optionally filtered by date (YYYY-MM-DD) "
        "or patient ID. Returns patient name, doctor, scheduled time, and status."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "description": "Optional date string formatted as YYYY-MM-DD to filter appointments.",
            },
            "patient_id": {
                "type": "string",
                "description": "Optional numeric patient ID string to view appointments for a specific patient.",
            },
        },
    },
    handler=_list_appointments,
)


# ---------------------------------------------------------------------------
# search_patient_registry
# ---------------------------------------------------------------------------

def _search_patient_registry(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    phone_number = arguments.get("phone_number", "").strip()
    name = arguments.get("name", "").strip()
    date_of_birth = arguments.get("date_of_birth", "").strip()

    client = BackendClient()
    params: dict[str, Any] = {}
    if phone_number:
        params["phone_number"] = phone_number
    elif name and date_of_birth:
        params["name"] = name
        params["date_of_birth"] = date_of_birth
    else:
        return {
            "error": "Provide either phone_number, or both name and date_of_birth (YYYY-MM-DD) to search.",
            "patients": [],
        }

    try:
        data = client.get("/api/patients/search/", bearer_token=context.bearer_token, params=params)
        results = data if isinstance(data, list) else data.get("results", [])
        return {
            "count": len(results),
            "patients": results,
        }
    except Exception as exc:
        logger.warning("Patient search returned error: %s", exc)
        return {
            "error": str(exc),
            "patients": [],
        }


search_patient_registry = Tool(
    name="search_patient_registry",
    description=(
        "Search for patients in the clinic administrative registry by phone number, "
        "or by name and date of birth (YYYY-MM-DD)."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "phone_number": {
                "type": "string",
                "description": "Patient phone number (e.g. '9876543210' or partial digits).",
            },
            "name": {
                "type": "string",
                "description": "Patient full name (required if phone_number is not provided).",
            },
            "date_of_birth": {
                "type": "string",
                "description": "Patient date of birth in YYYY-MM-DD format (required with name).",
            },
        },
    },
    handler=_search_patient_registry,
)


# ---------------------------------------------------------------------------
# schedule_appointment
# ---------------------------------------------------------------------------

def _schedule_appointment(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    patient_id = arguments["patient_id"]
    doctor_id = arguments["doctor_id"]
    scheduled_at = arguments["scheduled_at"]
    reason = arguments.get("reason", "Consultation")

    client = BackendClient()
    payload = {
        "patient": int(patient_id),
        "doctor": int(doctor_id),
        "scheduled_at": scheduled_at.strip(),
        "reason": reason.strip() if reason else "Consultation",
    }

    result = client.post("/api/appointments/", bearer_token=context.bearer_token, json_data=payload)
    return {
        "status": "success",
        "message": f"Appointment successfully scheduled for patient #{patient_id} with doctor #{doctor_id}.",
        "appointment": result,
    }


schedule_appointment = Tool(
    name="schedule_appointment",
    description=(
        "Book a new clinic appointment for a patient with an assigned doctor. "
        "Requires patient_id, doctor_id, scheduled_at (ISO8601 datetime), and reason."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "patient_id": {
                "type": "string",
                "description": "Numeric ID string of the patient (e.g. '39').",
            },
            "doctor_id": {
                "type": "string",
                "description": "Numeric ID string of the doctor (e.g. '1').",
            },
            "scheduled_at": {
                "type": "string",
                "description": "ISO8601 formatted datetime string (e.g. '2026-09-08T10:30:00Z').",
            },
            "reason": {
                "type": "string",
                "description": "Purpose or reason for the visit (e.g. 'Follow-up review').",
            },
        },
        "required": ["patient_id", "doctor_id", "scheduled_at"],
    },
    handler=_schedule_appointment,
)


# ---------------------------------------------------------------------------
# update_appointment_status
# ---------------------------------------------------------------------------

def _update_appointment_status(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    appointment_id = arguments["appointment_id"]
    status = arguments["status"]
    notes = arguments.get("notes", "")

    valid_statuses = {"SCHEDULED", "COMPLETED", "CANCELLED", "NO_SHOW"}
    norm_status = status.upper().strip()
    if norm_status not in valid_statuses:
        return {
            "error": f"Invalid status '{status}'. Must be one of: {', '.join(sorted(valid_statuses))}"
        }

    client = BackendClient()
    payload: dict[str, Any] = {"status": norm_status}
    if notes and notes.strip():
        payload["notes"] = notes.strip()

    result = client.patch(f"/api/appointments/{int(appointment_id)}/", bearer_token=context.bearer_token, json_data=payload)
    return {
        "status": "success",
        "message": f"Appointment #{appointment_id} updated to {norm_status}.",
        "appointment": result,
    }


update_appointment_status = Tool(
    name="update_appointment_status",
    description=(
        "Update the status of an existing appointment (e.g. SCHEDULED, COMPLETED, CANCELLED, NO_SHOW). "
        "Requires appointment_id and new status."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "appointment_id": {
                "type": "string",
                "description": "Numeric ID string of the appointment (e.g. '5').",
            },
            "status": {
                "type": "string",
                "description": "New status (one of 'SCHEDULED', 'COMPLETED', 'CANCELLED', 'NO_SHOW').",
            },
            "notes": {
                "type": "string",
                "description": "Optional receptionist notes or intake comments.",
            },
        },
        "required": ["appointment_id", "status"],
    },
    handler=_update_appointment_status,
)


# ---------------------------------------------------------------------------
# list_available_doctors
# ---------------------------------------------------------------------------

def _list_available_doctors(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    client = BackendClient()
    data = client.get("/api/auth/doctors/", bearer_token=context.bearer_token)
    doctors = data if isinstance(data, list) else data.get("results", [])

    formatted = []
    for doc in doctors:
        name = " ".join(filter(None, [doc.get("first_name", ""), doc.get("last_name", "")])) or doc.get("username") or doc.get("email") or ""
        formatted.append({
            "id": doc.get("id"),
            "name": f"Dr. {name}" if not name.startswith("Dr.") else name,
            "email": doc.get("email"),
            "specialization": doc.get("specialization") or "General Medicine",
            "phone_number": doc.get("phone_number"),
        })

    return {
        "count": len(formatted),
        "doctors": formatted,
    }


list_available_doctors = Tool(
    name="list_available_doctors",
    description="Retrieve the list of all active clinic doctors and their specializations.",
    parameters_json_schema={
        "type": "object",
        "properties": {},
    },
    handler=_list_available_doctors,
)


# ---------------------------------------------------------------------------
# register_patient
# ---------------------------------------------------------------------------

def _register_patient(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    full_name = str(arguments.get("full_name", "")).strip()
    date_of_birth_raw = str(arguments.get("date_of_birth", "")).strip()
    doctor_id = arguments.get("doctor_id")
    gender = str(arguments.get("gender", "")).strip().lower()
    phone_number = str(arguments.get("phone_number", "")).strip()
    address = str(arguments.get("address", "")).strip()
    caretaker_name = str(arguments.get("caretaker_name", "")).strip()
    caretaker_relationship = str(arguments.get("caretaker_relationship", "")).strip()
    caretaker_phone_number = str(arguments.get("caretaker_phone_number", "")).strip()
    caretaker_email = str(arguments.get("caretaker_email", "")).strip()

    if not full_name:
        return {"error": "Patient full_name is required to register a new patient."}
    if not date_of_birth_raw:
        return {"error": "Patient date_of_birth is required (e.g. YYYY-MM-DD or DD MM YYYY)."}

    dob = _normalize_dob(date_of_birth_raw)

    client = BackendClient()

    # Determine doctor_id if not explicitly provided
    resolved_doctor_id: int | None = None
    if doctor_id is not None and str(doctor_id).strip():
        try:
            resolved_doctor_id = int(doctor_id)
        except (ValueError, TypeError):
            pass

    if resolved_doctor_id is None:
        try:
            docs_data = client.get("/api/auth/doctors/", bearer_token=context.bearer_token)
            docs = docs_data if isinstance(docs_data, list) else docs_data.get("results", [])
            if docs:
                resolved_doctor_id = int(docs[0]["id"])
            else:
                resolved_doctor_id = 1
        except Exception:
            resolved_doctor_id = 1

    payload: dict[str, Any] = {
        "full_name": full_name,
        "date_of_birth": dob,
        "doctor": resolved_doctor_id,
    }
    if gender in {"male", "female", "other"}:
        payload["gender"] = gender
    if phone_number:
        payload["phone_number"] = phone_number
    if address:
        payload["address"] = address
    if caretaker_name:
        payload["caretaker_name"] = caretaker_name
    if caretaker_relationship:
        payload["caretaker_relationship"] = caretaker_relationship
    if caretaker_phone_number:
        payload["caretaker_phone_number"] = caretaker_phone_number
    if caretaker_email:
        payload["caretaker_email"] = caretaker_email

    try:
        created_patient = client.post("/api/patients/", bearer_token=context.bearer_token, json_data=payload)
    except Exception as exc:
        logger.error("Failed to register patient %s: %s", full_name, exc)
        return {
            "error": f"Failed to register patient: {str(exc)}",
            "status": "error",
        }

    patient_id = created_patient.get("id")
    doctor_name = created_patient.get("doctor_name") or f"Doctor #{resolved_doctor_id}"

    # Automatically generate invitation code for patient portal access
    invitation_code = None
    invitation_expires_at = None
    if patient_id:
        try:
            invite_data = client.post(
                "/api/invitations/generate/",
                bearer_token=context.bearer_token,
                json_data={"patient_id": patient_id},
            )
            invitation_code = invite_data.get("code")
            invitation_expires_at = invite_data.get("expires_at")
        except Exception as exc:
            logger.warning("Patient #%s created but invite generation failed: %s", patient_id, exc)

    return {
        "status": "success",
        "patient_id": patient_id,
        "full_name": created_patient.get("full_name", full_name),
        "date_of_birth": created_patient.get("date_of_birth", dob),
        "doctor_id": resolved_doctor_id,
        "doctor_name": doctor_name,
        "invitation_code": invitation_code,
        "invitation_expires_at": invitation_expires_at,
        "message": (
            f"Patient '{full_name}' was successfully registered with {doctor_name} (Patient ID #{patient_id}). "
            f"Portal invitation code: {invitation_code}"
            if invitation_code else
            f"Patient '{full_name}' was successfully registered with {doctor_name} (Patient ID #{patient_id})."
        ),
        "patient": created_patient,
    }


register_patient = Tool(
    name="register_patient",
    description=(
        "Register a new patient into the clinic registry and automatically generate a portal invitation code. "
        "Requires full_name and date_of_birth (accepts YYYY-MM-DD or standard date format like '21 08 2005'). "
        "Optional parameters: doctor_id, gender ('male', 'female', 'other'), phone_number, address, "
        "caretaker_name, caretaker_relationship, caretaker_phone_number, caretaker_email."
    ),
    parameters_json_schema={
        "type": "object",
        "properties": {
            "full_name": {
                "type": "string",
                "description": "Patient's full name (e.g. 'Zynab Mathiya').",
            },
            "date_of_birth": {
                "type": "string",
                "description": "Patient's date of birth in YYYY-MM-DD or date format (e.g. '2005-08-21' or '21 08 2005').",
            },
            "doctor_id": {
                "type": "string",
                "description": "Optional numeric ID string of the assigned doctor. Defaults to the primary clinic doctor if omitted.",
            },
            "gender": {
                "type": "string",
                "description": "Optional gender ('male', 'female', or 'other').",
            },
            "phone_number": {
                "type": "string",
                "description": "Optional contact phone number of the patient.",
            },
            "address": {
                "type": "string",
                "description": "Optional residential address.",
            },
            "caretaker_name": {
                "type": "string",
                "description": "Optional caretaker full name.",
            },
            "caretaker_relationship": {
                "type": "string",
                "description": "Optional caretaker relationship (e.g. 'Mother', 'Spouse', 'Guardian').",
            },
            "caretaker_phone_number": {
                "type": "string",
                "description": "Optional caretaker phone number.",
            },
            "caretaker_email": {
                "type": "string",
                "description": "Optional caretaker email address.",
            },
        },
        "required": ["full_name", "date_of_birth"],
    },
    handler=_register_patient,
)


# ---------------------------------------------------------------------------
# generate_invitation_code
# ---------------------------------------------------------------------------

def _generate_invitation_code(arguments: dict[str, Any], context: ToolContext) -> dict[str, Any]:
    patient_id = arguments.get("patient_id")
    if not patient_id:
        return {"error": "patient_id is required to generate an invitation code."}

    client = BackendClient()
    try:
        invite_data = client.post(
            "/api/invitations/generate/",
            bearer_token=context.bearer_token,
            json_data={"patient_id": int(patient_id)},
        )
        return {
            "status": "success",
            "patient_id": patient_id,
            "invitation_code": invite_data.get("code"),
            "expires_at": invite_data.get("expires_at"),
            "patient_name": invite_data.get("patient_name"),
            "message": f"Invitation code '{invite_data.get('code')}' generated for patient #{patient_id}.",
        }
    except Exception as exc:
        logger.error("Failed to generate invitation code for patient %s: %s", patient_id, exc)
        return {
            "error": f"Failed to generate invitation code: {str(exc)}",
            "status": "error",
        }


generate_invitation_code = Tool(
    name="generate_invitation_code",
    description="Generate a new portal signup invitation code for an existing registered patient.",
    parameters_json_schema={
        "type": "object",
        "properties": {
            "patient_id": {
                "type": "string",
                "description": "Numeric ID string of the patient (e.g. '40').",
            },
        },
        "required": ["patient_id"],
    },
    handler=_generate_invitation_code,
)

