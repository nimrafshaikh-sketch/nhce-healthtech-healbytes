"""Tool abstraction and registry - the strict execution boundary between
Gemini's decisions and any real action.

Gemini never runs code and never touches the database directly. It may
only *select* a tool by name and supply arguments matching that tool's
declared JSON Schema; this module is what turns that selection into an
actual (bounded, validated, auditable) function call.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from app.agents.exceptions import (
    InvalidToolCallError,
    ToolExecutionError,
    ToolNotFoundError,
    UnauthorizedError,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ToolContext:
    """Per-request authorization context forwarded to a tool.

    The agent foundation never creates, widens, or substitutes its own
    authority: `bearer_token` is the caller's own credential, forwarded
    as-is so the existing backend's own authentication/RBAC decides what
    is actually allowed. A tool with no `bearer_token` must fail rather
    than fall back to some elevated or service-level identity.
    """

    bearer_token: str | None = None


ToolHandler = Callable[[dict[str, Any], ToolContext], dict[str, Any]]


@dataclass(frozen=True)
class Tool:
    """One controlled action Gemini may choose to invoke.

    `parameters_json_schema` is a standard JSON Schema object describing
    the accepted arguments. It is shown to Gemini as the tool's contract,
    and it is also enforced here before `handler` ever runs, so a
    malformed or out-of-contract call from the model never reaches real
    code.
    """

    name: str
    description: str
    parameters_json_schema: dict[str, Any]
    handler: ToolHandler

    def validate_arguments(self, arguments: dict[str, Any]) -> None:
        """Structural validation against the declared schema.

        Deliberately not a full JSON Schema validator (no new dependency
        for a hackathon MVP) - it enforces the two properties that matter
        for a strict boundary: only declared properties are accepted, and
        every `required` property is present.
        """

        if not isinstance(arguments, dict):
            raise InvalidToolCallError(
                f"Tool '{self.name}' expects an object of arguments, "
                f"got {type(arguments).__name__}."
            )
        properties = self.parameters_json_schema.get("properties", {})
        required = self.parameters_json_schema.get("required", [])
        unknown = set(arguments) - set(properties)
        if unknown:
            raise InvalidToolCallError(
                f"Tool '{self.name}' received unknown argument(s): {sorted(unknown)}."
            )
        missing = [name for name in required if name not in arguments]
        if missing:
            raise InvalidToolCallError(
                f"Tool '{self.name}' is missing required argument(s): {missing}."
            )


class ToolRegistry:
    """The fixed set of actions Gemini is allowed to select from.

    This is the strict execution boundary called for in the project
    instructions: Gemini never runs arbitrary code, never queries the
    database, and can only ever reach a function that has been explicitly
    registered here under a known name.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered.")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise ToolNotFoundError(f"No tool named '{name}' is registered.") from None

    def function_declarations(self) -> list[dict[str, Any]]:
        """Tool specs in the shape the Gemini client turns into function
        declarations (see `app/agents/gemini_client.py`)."""

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters_json_schema": tool.parameters_json_schema,
            }
            for tool in self._tools.values()
        ]

    def execute(
        self, name: str, arguments: dict[str, Any], context: ToolContext
    ) -> dict[str, Any]:
        """Validate and run one tool call, returning its JSON-serializable result.

        Raises `ToolNotFoundError` / `InvalidToolCallError` for a malformed
        call from Gemini, or `ToolExecutionError` if the tool itself fails
        (including the existing backend rejecting the call, e.g. a 403 from
        its own RBAC) - the caller decides how to surface each case.
        """

        tool = self.get(name)
        tool.validate_arguments(arguments)
        logger.info("Executing tool '%s' with arguments %s", name, arguments)
        try:
            result = tool.handler(arguments, context)
        except (ToolExecutionError, InvalidToolCallError, ToolNotFoundError, UnauthorizedError):
            raise
        except Exception as exc:  # noqa: BLE001 - any other tool failure becomes ToolExecutionError
            raise ToolExecutionError(f"Tool '{name}' failed: {exc}") from exc
        if not isinstance(result, dict):
            raise ToolExecutionError(f"Tool '{name}' returned a non-JSON-object result.")
        return result
