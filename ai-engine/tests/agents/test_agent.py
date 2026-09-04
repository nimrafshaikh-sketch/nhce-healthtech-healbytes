"""Tests for the agent orchestration loop (`app/agents/agent.py`).

`GeminiClient` is fully mocked here - these tests exercise the loop logic
(when to call a tool, how a tool result and its failures are surfaced,
the iteration cap) independent of any real Gemini or backend call.
"""

from unittest.mock import MagicMock

import pytest
from google.genai import types

from app.agents.agent import Agent, AgentError
from app.agents.gemini_client import ModelTurn
from app.agents.tools.base import Tool, ToolContext, ToolRegistry


def _text_turn(text: str) -> ModelTurn:
    return ModelTurn(
        text=text,
        function_calls=[],
        raw_content=types.Content(role="model", parts=[types.Part(text=text)]),
    )


def _function_call_turn(name: str, args: dict) -> ModelTurn:
    return ModelTurn(
        text=None,
        function_calls=[types.FunctionCall(name=name, args=args)],
        raw_content=types.Content(
            role="model",
            parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))],
        ),
    )


def _registry_with_echo() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(
        Tool(
            name="echo",
            description="Echoes back a value.",
            parameters_json_schema={
                "type": "object",
                "properties": {"value": {"type": "string"}},
                "required": ["value"],
            },
            handler=lambda args, ctx: {"echoed": args["value"]},
        )
    )
    return registry


def test_direct_text_reply_without_any_tool_call():
    gemini = MagicMock()
    gemini.generate.return_value = _text_turn("Hello, how can I help?")

    agent = Agent("system", _registry_with_echo(), gemini_client=gemini)
    result = agent.run(message="hi", context=ToolContext())

    assert result.reply == "Hello, how can I help?"
    assert result.tool_calls == []
    gemini.generate.assert_called_once()


def test_single_successful_tool_round_trip():
    gemini = MagicMock()
    gemini.generate.side_effect = [
        _function_call_turn("echo", {"value": "ping"}),
        _text_turn("The tool said: ping"),
    ]

    agent = Agent("system", _registry_with_echo(), gemini_client=gemini)
    result = agent.run(message="please echo ping", context=ToolContext())

    assert result.reply == "The tool said: ping"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "echo"
    assert result.tool_calls[0].succeeded is True
    assert gemini.generate.call_count == 2

    # Second call must include the function-call turn and the function
    # response turn appended to the conversation.
    second_call_contents = gemini.generate.call_args_list[1].kwargs["contents"]
    assert len(second_call_contents) == 3  # user message, model call, function response


def test_unknown_tool_name_is_reported_to_gemini_not_raised():
    gemini = MagicMock()
    gemini.generate.side_effect = [
        _function_call_turn("does_not_exist", {}),
        _text_turn("Sorry, that action is not available."),
    ]

    agent = Agent("system", _registry_with_echo(), gemini_client=gemini)
    result = agent.run(message="do something unsupported", context=ToolContext())

    assert result.reply == "Sorry, that action is not available."
    assert result.tool_calls[0].succeeded is False
    assert "does_not_exist" in result.tool_calls[0].tool_name


def test_missing_bearer_token_surfaces_as_unauthorized_outcome():
    registry = ToolRegistry()

    def _needs_auth(args, ctx: ToolContext):
        if not ctx.bearer_token:
            from app.agents.exceptions import UnauthorizedError

            raise UnauthorizedError("no token")
        return {"ok": True}

    registry.register(
        Tool(
            name="needs_auth",
            description="Requires a bearer token.",
            parameters_json_schema={"type": "object", "properties": {}},
            handler=_needs_auth,
        )
    )

    gemini = MagicMock()
    gemini.generate.side_effect = [
        _function_call_turn("needs_auth", {}),
        _text_turn("I could not access that without authorization."),
    ]

    agent = Agent("system", registry, gemini_client=gemini)
    result = agent.run(message="try the protected action", context=ToolContext(bearer_token=None))

    assert result.tool_calls[0].succeeded is False
    assert "Unauthorized" in result.tool_calls[0].summary


def test_exceeding_max_tool_iterations_raises_agent_error():
    gemini = MagicMock()
    gemini.generate.return_value = _function_call_turn("echo", {"value": "loop"})

    agent = Agent("system", _registry_with_echo(), gemini_client=gemini, max_tool_iterations=2)

    with pytest.raises(AgentError):
        agent.run(message="loop forever", context=ToolContext())

    assert gemini.generate.call_count == 2
