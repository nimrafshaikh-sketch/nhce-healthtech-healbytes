"""Agent foundation demo route.

Proves the full Phase 1 flow end-to-end with the one read-only
proof-of-concept tool:

    User request -> Agent -> Gemini -> tool/function selection
        -> Tool Registry -> existing backend/service (HTTP)
        -> result returned to Gemini -> final natural-language response

No Doctor Agent or Receptionist Agent is implemented here - this is a
single, role-agnostic demo endpoint for Phase 1 only, per the project
instructions. A role-specific agent in a later phase gets its own route
the same way, with its own system instruction and `ToolRegistry`.
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
from app.agents.tools.default_registry import build_default_registry
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

_SYSTEM_INSTRUCTION = (
    "You are the HealBytes clinical-workflow assistant foundation. You may "
    "only act by calling one of the tools you have been given - you have "
    "no other way to read or change any data, and no direct database or "
    "code-execution access. If a tool call fails or is unauthorized, say "
    "so plainly instead of guessing or inventing an answer. Never provide "
    "a medical diagnosis, treatment plan, or emergency instruction - "
    "defer to the existing deterministic AI Engine analysis and the care "
    "team for that."
)


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    auth = authorization.strip()
    if not auth:
        return None
    if auth.lower().startswith("bearer "):
        return auth[7:].strip() or None
    if auth.count(".") == 2 and " " not in auth:
        return auth
    return None


@router.post("/agents/patient-summary", response_model=AgentChatResponse, tags=["agents"])
def run_patient_summary_agent(
    payload: AgentChatRequest,
    authorization: str | None = Header(default=None),
) -> AgentChatResponse:
    """Run one proof-of-concept agent turn.

    Forwards the caller's own bearer token so the existing backend's
    authentication/RBAC - not this service - decides what the
    `get_patient_basic_info` tool is allowed to return. This endpoint
    makes no authorization decisions of its own and never touches a
    database directly.
    """

    bearer_token = _extract_bearer_token(authorization) or _extract_bearer_token(payload.auth_token)
    context = ToolContext(bearer_token=bearer_token)
    history = [(turn.role, turn.text) for turn in payload.conversation_history]

    agent = Agent(
        system_instruction=_SYSTEM_INSTRUCTION,
        tool_registry=build_default_registry(),
    )

    try:
        result: AgentResult = agent.run(message=payload.message, context=context, history=history)
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
        logger.error("Agent turn %s misconfigured: %s", payload.request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)
        ) from exc
    except (GeminiAPIError, MalformedModelResponseError) as exc:
        logger.error("Agent turn %s failed talking to Gemini: %s", payload.request_id, exc)
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc
    except AgentError as exc:
        logger.error("Agent turn %s failed: %s", payload.request_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)
        ) from exc
    except Exception:
        logger.exception("Unexpected error running agent turn %s", payload.request_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal error while running the agent.",
        )
