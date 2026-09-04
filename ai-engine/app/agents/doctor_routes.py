"""Doctor Agent (Phase 2).

The first role-specific agent built on the Phase 1 foundation, exactly per
that foundation's own "adding a new agent" guidance
(`app/agents/README.md`): a different system instruction plus a different
`ToolRegistry`, reusing `Agent`, `GeminiClient`, `ToolContext`, and the
request/response schemas unchanged.

    Doctor JWT -> Doctor Agent -> Gemini -> tool/function selection
        -> Tool Registry -> existing backend/AI Engine (HTTP)
        -> real authorized patient data -> Gemini -> grounded response

Gemini is the reasoning/orchestration layer only. Every fact it can use
comes from a tool call into the existing, already-authorized backend; the
deterministic AI Engine capabilities (risk, adherence, trend/history,
follow-up) remain the source of truth for those calculations - this agent
never asks Gemini to recompute them.

No Receptionist/Patient/appointment agent is implemented here - Doctor
Agent only, per this phase's scope.
"""

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
from app.agents.tools.doctor_registry import build_doctor_registry
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

DOCTOR_SYSTEM_INSTRUCTION = (
    "You are an AI assistant supporting an authorized doctor using the "
    "HealBytes clinical platform. You may act ONLY by calling the tools "
    "you have been given - you have no other way to read any data, and no "
    "direct database, RAG, or code-execution access of your own.\n\n"
    "Rules you must follow at all times:\n"
    "- Retrieve patient facts using the available tools; never invent, "
    "guess, or assume patient information that no tool returned.\n"
    "- Never claim or imply that a tool was called if it was not, and "
    "never fabricate a tool result.\n"
    "- Use the existing clinical analysis results returned by the tools "
    "(risk level/score, medication adherence, trends, follow-up "
    "recommendations) as-is; you are the orchestration/reasoning layer, "
    "not a replacement for that deterministic analysis - never recompute "
    "or second-guess those numbers yourself.\n"
    "- Clearly distinguish retrieved facts from your own explanation or "
    "recommendation in your response.\n"
    "- Do not make unsupported diagnoses or invent a medical conclusion "
    "beyond what the tool results and the existing AI Engine analysis "
    "support.\n"
    "- Respect patient authorization and privacy: only discuss the patient "
    "identified in this conversation, and only using tool results that "
    "actually came back successfully.\n"
    "- If a tool call fails, is unauthorized, or returns no data, say so "
    "plainly rather than guessing.\n"
    "- Use the patient-record search tool only for the authorized patient "
    "already established in this conversation.\n"
    "- Keep responses concise and clinically useful - a short, scannable "
    "summary, not an exhaustive dump of every field.\n"
    "- Do not call every available tool for every question: pick only the "
    "tool(s) that the doctor's actual question needs (e.g. a question "
    "about medication adherence alone should not also call risk, history, "
    "or RAG search)."
)


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    auth = authorization.strip()
    if not auth:
        return None
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    # If the user pasted the raw JWT token directly without "Bearer "
    if auth.count(".") == 2 and " " not in auth:
        return auth
    return None


@router.post("/agents/doctor", response_model=AgentChatResponse, tags=["doctor-agent"])
def run_doctor_agent(
    payload: AgentChatRequest,
    authorization: str | None = Header(default=None),
) -> AgentChatResponse:
    """Run one Doctor Agent turn about a specific patient.

    Requires `patient_id` on the request (a doctor's clinical question is
    always about a specific patient) and forwards the caller's own bearer
    token so the existing backend's authentication/RBAC - not this
    service - decides what each tool call is allowed to return. This
    endpoint makes no authorization decisions of its own, never touches a
    database directly, and never exposes internal tokens, API keys, or
    implementation details in its response.
    """

    logger.info("Running Doctor Agent turn %s", payload.request_id)

    if not payload.patient_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="patient_id is required for the Doctor Agent.",
        )

    bearer_token = _extract_bearer_token(authorization) or _extract_bearer_token(payload.auth_token)
    if not bearer_token:
        # Every Doctor Agent tool needs the caller's own credentials to
        # reach the backend (see app/agents/tools/doctor_tools.py); unlike
        # the Phase 1 generic demo agent, there is no useful Doctor Agent
        # turn that doesn't eventually need one, so this fails closed here
        # rather than spending a Gemini call just to fail at the tool
        # boundary.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid Doctor JWT access token is required. Provide it in the Authorization header or via the 'auth_token' field in the request body.",
        )

    context = ToolContext(bearer_token=bearer_token)
    history = [(turn.role, turn.text) for turn in payload.conversation_history]

    agent = Agent(
        system_instruction=DOCTOR_SYSTEM_INSTRUCTION,
        tool_registry=build_doctor_registry(),
    )

    message = f"[Patient ID: {payload.patient_id}] {payload.message}"

    try:
        result: AgentResult = agent.run(message=message, context=context, history=history)
        return AgentChatResponse(
            request_id=payload.request_id,
            reply=result.reply,
            tool_calls=[
                ToolCallRecord(
                    tool_name=outcome.tool_name,
                    arguments=outcome.arguments,
                    succeeded=outcome.succeeded,
                    summary=outcome.summary,
                )
                for outcome in result.tool_calls
            ],
            model_version=settings.gemini_model,
        )
    except GeminiConfigError as exc:
        logger.error("Doctor Agent turn %s misconfigured: %s", payload.request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except (GeminiAPIError, MalformedModelResponseError) as exc:
        logger.error("Doctor Agent turn %s failed talking to Gemini: %s", payload.request_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except AgentError as exc:
        logger.error("Doctor Agent turn %s failed: %s", payload.request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    except Exception:
        logger.exception("Unexpected error running Doctor Agent turn %s", payload.request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while running the Doctor Agent.",
        )
