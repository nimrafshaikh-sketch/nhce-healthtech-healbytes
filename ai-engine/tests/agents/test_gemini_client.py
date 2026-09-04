"""Tests for `app/agents/gemini_client.py` error handling and response
parsing. No real network calls or API key are used anywhere here - the
`google.genai.Client` is always mocked.
"""

from unittest.mock import MagicMock, patch

import pytest
from google.genai import errors as genai_errors
from google.genai import types

from app.agents.exceptions import (
    GeminiAPIError,
    GeminiConfigError,
    MalformedModelResponseError,
)
from app.agents.gemini_client import GeminiClient


def test_missing_api_key_raises_config_error():
    client = GeminiClient(api_key="", model="gemini-flash-latest")
    with pytest.raises(GeminiConfigError):
        client.generate(system_instruction="hi", contents=[])


def _text_response(text: str) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(role="model", parts=[types.Part(text=text)])
            )
        ]
    )


def _function_call_response(name: str, args: dict) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[
            types.Candidate(
                content=types.Content(
                    role="model",
                    parts=[types.Part(function_call=types.FunctionCall(name=name, args=args))],
                )
            )
        ]
    )


@patch("app.agents.gemini_client.genai.Client")
def test_generate_returns_text_turn(mock_client_cls):
    mock_instance = MagicMock()
    mock_instance.models.generate_content.return_value = _text_response("hello there")
    mock_client_cls.return_value = mock_instance

    client = GeminiClient(api_key="fake-key", model="gemini-flash-latest")
    turn = client.generate(system_instruction="sys", contents=[])

    assert turn.text == "hello there"
    assert turn.function_calls == []


@patch("app.agents.gemini_client.genai.Client")
def test_generate_returns_function_call_turn(mock_client_cls):
    mock_instance = MagicMock()
    mock_instance.models.generate_content.return_value = _function_call_response(
        "get_patient_basic_info", {"patient_id": "42"}
    )
    mock_client_cls.return_value = mock_instance

    client = GeminiClient(api_key="fake-key", model="gemini-flash-latest")
    turn = client.generate(system_instruction="sys", contents=[])

    assert turn.text is None
    assert len(turn.function_calls) == 1
    assert turn.function_calls[0].name == "get_patient_basic_info"
    assert turn.function_calls[0].args == {"patient_id": "42"}


@patch("app.agents.gemini_client.genai.Client")
def test_api_error_is_wrapped(mock_client_cls):
    mock_instance = MagicMock()
    mock_instance.models.generate_content.side_effect = genai_errors.ClientError(
        code=429, response_json={"error": {"message": "quota exceeded"}}
    )
    mock_client_cls.return_value = mock_instance

    client = GeminiClient(api_key="fake-key", model="gemini-flash-latest")
    with pytest.raises(GeminiAPIError):
        client.generate(system_instruction="sys", contents=[])


@patch("app.agents.gemini_client.genai.Client")
def test_no_candidates_raises_malformed_response(mock_client_cls):
    mock_instance = MagicMock()
    mock_instance.models.generate_content.return_value = types.GenerateContentResponse(
        candidates=[]
    )
    mock_client_cls.return_value = mock_instance

    client = GeminiClient(api_key="fake-key", model="gemini-flash-latest")
    with pytest.raises(MalformedModelResponseError):
        client.generate(system_instruction="sys", contents=[])


@patch("app.agents.gemini_client.genai.Client")
def test_empty_text_raises_malformed_response(mock_client_cls):
    mock_instance = MagicMock()
    mock_instance.models.generate_content.return_value = _text_response("   ")
    mock_client_cls.return_value = mock_instance

    client = GeminiClient(api_key="fake-key", model="gemini-flash-latest")
    with pytest.raises(MalformedModelResponseError):
        client.generate(system_instruction="sys", contents=[])
