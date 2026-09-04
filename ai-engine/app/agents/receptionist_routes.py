"""Receptionist Agent routes and execution endpoint.

Allows clinic receptionists and front-desk staff to query doctor rosters,
look up patients, list and filter appointments, book new appointments,
and update appointment statuses using conversational AI with Gemini tool calling.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Header, HTTPException, status

from app.agents.agent import Agent, AgentResult
from app.agents.exceptions import (
    AgentError,
    GeminiAPIError,
    GeminiConfigError,
    MalformedModelResponseError,
)
from app.agents.schemas import AgentChatRequest, AgentChatResponse, ToolCallRecord
from app.agents.tools.base import ToolContext
from app.agents.tools.receptionist_registry import build_receptionist_registry
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

RECEPTIONIST_SYSTEM_INSTRUCTION = (
    "You are an AI Front-Desk Assistant supporting the Receptionist staff at the "
    "HealBytes clinical practice. You assist with appointment scheduling, searching "
    "patient registries, registering new patients, generating patient portal invitation codes, "
    "checking doctor availability, and updating appointment statuses.\n\n"
    "Rules you must follow at all times:\n"
    "- You act ONLY by calling the tools you have been provided; never invent, guess, "
    "or assume appointments, patient information, or doctor schedules.\n"
    "- If asked to add, create, or register a new patient (e.g. 'add patient Zynab Mathiya DOB 21 08 2005'), "
    "call register_patient with full_name, date_of_birth (pass the date provided or normalized YYYY-MM-DD), "
    "and any optional parameters given (such as gender, phone_number, address, doctor_id). "
    "Always state the registered patient name, patient ID, assigned doctor, and clearly present the generated "
    "portal invitation code in your reply so the receptionist can provide it to the patient.\n"
    "- If a critical detail like full_name or date_of_birth is missing when asked to add a patient, "
    "politely ask the receptionist for the missing information.\n"
    "- If asked to generate an invitation code for an existing patient, call generate_invitation_code.\n"
    "- If asked about appointments for a date or patient, call list_appointments.\n"
    "- If asked to find or look up a patient, call search_patient_registry with phone_number "
    "or name and date_of_birth.\n"
    "- If asked to book an appointment: check if patient_id, doctor_id, date/time, and reason are provided. "
    "If a patient name is mentioned, look them up using search_patient_registry to get their patient ID. "
    "If doctor is omitted, check list_available_doctors to find the available doctor. "
    "If essential details like patient name or preferred time slot are missing (e.g. 'book appointment on 6 sept'), "
    "check the schedule for that date via list_appointments and list_available_doctors, then politely ask the receptionist "
    "for the patient's name/ID and desired time slot.\n"
    "- If asked to update an appointment (e.g. check-in, complete, cancel), call update_appointment_status.\n"
    "- If asked about available doctors or specializations, call list_available_doctors.\n"
    "- Keep your responses polite, professional, concise, and structured for fast front-desk reference."
)



def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    auth = authorization.strip()
    if not auth:
        return None
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    return auth


@router.post("/agents/receptionist", response_model=AgentChatResponse, tags=["receptionist-agent"])
def run_receptionist_agent(
    payload: AgentChatRequest,
    authorization: str | None = Header(default=None),
) -> AgentChatResponse:
    """Run one Receptionist Agent turn.

    Forwards the receptionist's own bearer token so existing backend RBAC
    governs every tool execution.
    """
    logger.info("Running Receptionist Agent turn %s", payload.request_id)

    bearer_token = _extract_bearer_token(authorization) or _extract_bearer_token(payload.auth_token)
    if not bearer_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid Receptionist JWT access token is required. Provide it in the Authorization header or via 'auth_token'.",
        )

    context = ToolContext(bearer_token=bearer_token)
    history = [(turn.role, turn.text) for turn in payload.conversation_history]

    agent = Agent(
        system_instruction=RECEPTIONIST_SYSTEM_INSTRUCTION,
        tool_registry=build_receptionist_registry(),
    )

    message = payload.message
    if payload.patient_id and payload.patient_id.strip():
        message = f"[Active Patient ID: {payload.patient_id}] {payload.message}"

    try:
        result: AgentResult = agent.run(
            message=message,
            context=context,
            history=history,
        )
        return AgentChatResponse(
            request_id=payload.request_id,
            reply=result.reply,
            tool_calls=[
                ToolCallRecord(
                    tool_name=tc.tool_name,
                    arguments=tc.arguments,
                    succeeded=tc.succeeded,
                    summary=tc.summary,
                )
                for tc in result.tool_calls
            ],
            model_version=settings.gemini_model,
        )
    except GeminiConfigError as exc:
        logger.error("Receptionist Agent turn %s misconfigured: %s", payload.request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except (GeminiAPIError, MalformedModelResponseError) as exc:
        logger.error("Receptionist Agent turn %s failed talking to Gemini: %s", payload.request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc
    except AgentError as exc:
        logger.error("Receptionist Agent turn %s failed: %s", payload.request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    except Exception:
        logger.exception("Unexpected error running Receptionist Agent turn %s", payload.request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while running the Receptionist Agent.",
        )
