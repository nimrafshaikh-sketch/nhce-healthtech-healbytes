"""Tests for the strict tool execution boundary (`app/agents/tools/base.py`)."""

import pytest

from app.agents.exceptions import InvalidToolCallError, ToolExecutionError, ToolNotFoundError
from app.agents.tools.base import Tool, ToolContext, ToolRegistry


def _echo_tool() -> Tool:
    return Tool(
        name="echo",
        description="Echoes back the supplied value.",
        parameters_json_schema={
            "type": "object",
            "properties": {"value": {"type": "string"}},
            "required": ["value"],
        },
        handler=lambda args, ctx: {"echoed": args["value"]},
    )


def test_register_and_execute_success():
    registry = ToolRegistry()
    registry.register(_echo_tool())

    result = registry.execute("echo", {"value": "hi"}, ToolContext(bearer_token="t"))

    assert result == {"echoed": "hi"}


def test_duplicate_registration_rejected():
    registry = ToolRegistry()
    registry.register(_echo_tool())
    with pytest.raises(ValueError):
        registry.register(_echo_tool())


def test_unknown_tool_name_raises_tool_not_found():
    registry = ToolRegistry()
    registry.register(_echo_tool())
    with pytest.raises(ToolNotFoundError):
        registry.execute("does_not_exist", {}, ToolContext())


def test_missing_required_argument_raises_invalid_tool_call():
    registry = ToolRegistry()
    registry.register(_echo_tool())
    with pytest.raises(InvalidToolCallError):
        registry.execute("echo", {}, ToolContext())


def test_unknown_argument_raises_invalid_tool_call():
    registry = ToolRegistry()
    registry.register(_echo_tool())
    with pytest.raises(InvalidToolCallError):
        registry.execute("echo", {"value": "hi", "extra": 1}, ToolContext())


def test_handler_exception_is_wrapped_as_tool_execution_error():
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="boom",
            description="Always fails.",
            parameters_json_schema={"type": "object", "properties": {}},
            handler=lambda args, ctx: (_ for _ in ()).throw(RuntimeError("kaboom")),
        )
    )
    with pytest.raises(ToolExecutionError):
        registry.execute("boom", {}, ToolContext())


def test_non_dict_handler_result_raises_tool_execution_error():
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="bad_return",
            description="Returns the wrong type.",
            parameters_json_schema={"type": "object", "properties": {}},
            handler=lambda args, ctx: "not a dict",
        )
    )
    with pytest.raises(ToolExecutionError):
        registry.execute("bad_return", {}, ToolContext())


def test_function_declarations_shape():
    registry = ToolRegistry()
    registry.register(_echo_tool())
    declarations = registry.function_declarations()
    assert declarations == [
        {
            "name": "echo",
            "description": "Echoes back the supplied value.",
            "parameters_json_schema": {
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
        }
    ]
