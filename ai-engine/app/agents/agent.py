"""Reusable agent foundation.

An `Agent` is just: a system instruction + a user message + caller-supplied
conversation history, run through Gemini with a fixed set of tool
declarations. When Gemini asks to call a tool, the agent executes it
through the `ToolRegistry` (never directly), sends the tool's result back
to Gemini, and repeats until Gemini returns a final natural-language
reply or a bounded iteration limit is hit.

A role-specific agent (Doctor, Receptionist - not built in Phase 1, see
the project instructions) is nothing more than a different system
instruction plus a `ToolRegistry` containing the tools that role is
allowed to use. See `app/agents/README.md` for how to add one.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from google.genai import types

from app.agents.exceptions import (
    AgentError,
    InvalidToolCallError,
    ToolExecutionError,
    ToolNotFoundError,
    UnauthorizedError,
)
from app.agents.gemini_client import GeminiClient
from app.agents.tools.base import ToolContext, ToolRegistry
from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class ToolCallOutcome:
    """A safe-to-return record of one tool invocation (see
    `app/agents/schemas.py::ToolCallRecord` for the API-facing shape).
    Deliberately excludes raw tool output, which may carry patient data.
    """

    tool_name: str
    arguments: dict
    succeeded: bool
    summary: str


@dataclass
class AgentResult:
    reply: str
    tool_calls: list[ToolCallOutcome] = field(default_factory=list)


class Agent:
    """Runs one user turn through Gemini, executing any tool calls it asks for."""

    def __init__(
        self,
        system_instruction: str,
        tool_registry: ToolRegistry,
        gemini_client: GeminiClient | None = None,
        max_tool_iterations: int | None = None,
    ) -> None:
        self._system_instruction = system_instruction
        self._tool_registry = tool_registry
        self._gemini_client = gemini_client or GeminiClient()
        self._max_tool_iterations = max_tool_iterations or settings.agent_max_tool_iterations

    def run(
        self,
        *,
        message: str,
        context: ToolContext,
        history: list[tuple[str, str]] | None = None,
    ) -> AgentResult:
        """Run one turn and return the final reply plus a tool-call trace.

        `history` is a list of `(role, text)` pairs (`role` in
        `{"user", "agent"}`), oldest first, supplied by the caller for
        context - like the rest of the AI Engine, the agent itself holds
        no session state between calls.

        Raises `AgentError` (or one of the more specific exceptions in
        `app/agents/exceptions.py`, e.g. `GeminiConfigError`,
        `GeminiAPIError`) if the turn cannot be completed.
        """

        contents: list[types.Content] = [
            types.Content(
                role="user" if role == "user" else "model",
                parts=[types.Part(text=text)],
            )
            for role, text in (history or [])
        ]
        contents.append(types.Content(role="user", parts=[types.Part(text=message)]))

        tool_declarations = self._tool_registry.function_declarations()
        outcomes: list[ToolCallOutcome] = []

        for _ in range(self._max_tool_iterations):
            turn = self._gemini_client.generate(
                system_instruction=self._system_instruction,
                contents=contents,
                tool_declarations=tool_declarations,
            )

            if not turn.function_calls:
                return AgentResult(reply=turn.text or "", tool_calls=outcomes)

            # Gemini's function-call turn becomes part of the running
            # conversation, exactly like the SDK's own reference loop.
            contents.append(turn.raw_content)

            response_parts: list[types.Part] = []
            for call in turn.function_calls:
                name = call.name or ""
                arguments = dict(call.args or {})
                function_response = self._execute_tool(name, arguments, context, outcomes)
                response_parts.append(
                    types.Part.from_function_response(name=name, response=function_response)
                )

            contents.append(types.Content(role="user", parts=response_parts))

        raise AgentError(
            f"Exceeded max_tool_iterations ({self._max_tool_iterations}) "
            "without reaching a final response."
        )

    def _execute_tool(
        self,
        name: str,
        arguments: dict,
        context: ToolContext,
        outcomes: list[ToolCallOutcome],
    ) -> dict:
        """Execute one tool call, recording the outcome and returning the
        function-response payload to send back to Gemini. Failures are
        reported *to Gemini* as a structured error (never raised out of
        this method) so a single bad tool call can't crash the whole
        turn - Gemini gets the chance to explain the failure in its final
        reply instead."""

        try:
            result = self._tool_registry.execute(name, arguments, context)
            outcomes.append(
                ToolCallOutcome(name, arguments, True, f"'{name}' completed successfully.")
            )
            return {"result": result}
        except UnauthorizedError as exc:
            logger.warning("Tool '%s' unauthorized: %s", name, exc)
            outcomes.append(ToolCallOutcome(name, arguments, False, f"Unauthorized: {exc}"))
            return {"error": "unauthorized", "message": str(exc)}
        except (ToolNotFoundError, InvalidToolCallError, ToolExecutionError) as exc:
            logger.warning("Tool '%s' failed: %s", name, exc)
            outcomes.append(ToolCallOutcome(name, arguments, False, f"Failed: {exc}"))
            return {"error": type(exc).__name__, "message": str(exc)}
