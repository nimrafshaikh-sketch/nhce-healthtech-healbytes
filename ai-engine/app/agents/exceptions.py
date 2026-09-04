"""Exceptions for the Gemini + agent foundation.

Each exception maps to exactly one failure mode called out in the Phase 1
scope, so `app/agents/routes.py` can translate each one into a clean,
specific HTTP response instead of a generic 500.
"""


class AgentError(Exception):
    """Base class for all agent-foundation errors."""


class GeminiConfigError(AgentError):
    """Gemini is not configured (e.g. missing `GEMINI_API_KEY`)."""


class GeminiAPIError(AgentError):
    """The Gemini API call itself failed (network, auth, quota, 5xx, ...)."""


class MalformedModelResponseError(AgentError):
    """Gemini returned a response this agent cannot safely interpret."""


class ToolNotFoundError(AgentError):
    """Gemini asked to call a tool name that isn't in the registry."""


class InvalidToolCallError(AgentError):
    """The tool call's arguments don't satisfy the tool's declared schema."""


class ToolExecutionError(AgentError):
    """A registered tool raised while executing (including backend errors)."""


class UnauthorizedError(AgentError):
    """The caller did not supply the credentials a tool needs to run.

    Raised *before* any tool executes (fail closed) or surfaced when the
    existing backend itself rejects the forwarded credentials - the agent
    never substitutes its own authority for the caller's.
    """
