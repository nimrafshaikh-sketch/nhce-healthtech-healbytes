"""Request/response contracts for the agent foundation's HTTP surface.

Separate from `app/schemas/` (the fixed `/analyze` and `/history/summary`
contracts) because this is a different capability with a different shape:
a natural-language message in, a natural-language reply out, plus a trace
of which tool(s) ran - not a structured clinical assessment.
"""

from typing import Any, Literal

from pydantic import Field

from app.schemas.common import NonEmptyStr, StrictModel


class AgentTurn(StrictModel):
    """One prior turn of a conversation, caller-supplied for context only."""

    role: Literal["user", "agent"]
    text: NonEmptyStr


class AgentChatRequest(StrictModel):
    """A single user turn sent to an agent.

    `conversation_history` is optional and caller-supplied - like the rest
    of the AI Engine, this service holds no session state and no database;
    a multi-turn caller resends prior turns each time.
    """

    request_id: NonEmptyStr
    message: NonEmptyStr
    patient_id: NonEmptyStr | None = Field(
        default=None,
        description=(
            "Patient the message concerns, if any. Tools decide whether "
            "they need this; it is never used to widen access beyond what "
            "the caller's own credentials already authorize."
        ),
    )
    conversation_history: list[AgentTurn] = Field(default_factory=list)
    auth_token: str | None = Field(
        default=None,
        description="Optional Doctor JWT access token if not passed in the Authorization header.",
    )


class ToolCallRecord(StrictModel):
    """One tool invocation the agent made while producing its reply.

    Returned for transparency/debugging - callers can see exactly which
    controlled action ran, with what arguments, and whether it succeeded.
    Never includes raw tool output (which may carry patient data); only a
    short, safe status summary.
    """

    tool_name: NonEmptyStr
    arguments: dict[str, Any]
    succeeded: bool
    summary: NonEmptyStr


class AgentChatResponse(StrictModel):
    """The agent's final natural-language reply plus its tool-call trace."""

    request_id: NonEmptyStr
    reply: NonEmptyStr
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    model_version: NonEmptyStr
