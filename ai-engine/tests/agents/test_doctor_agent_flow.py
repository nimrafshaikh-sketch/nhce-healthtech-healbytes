"""End-to-end Doctor Agent flow, using the REAL `Agent`, the REAL
`build_doctor_registry()`, and the REAL doctor tool handlers - only the
two network edges are mocked: `GeminiClient` (no real Gemini call) and
`BackendClient`'s underlying `httpx.get` (no real Django backend). This
is the closest thing to the real flow this test suite can exercise
without live credentials/services - see `app/agents/README.md` for the
real (live) smoke test procedure.

Covers items 2-5 and 10 of the Phase 2 test checklist: Gemini requesting
a tool, multiple tool calls in one request, tool results correctly
returned to Gemini, the final response being generated from those
results, and tool failure being handled without crashing the turn.
"""

from unittest.mock import MagicMock, patch

import pytest
from google.genai import types

from app.agents.agent import Agent
from app.agents.gemini_client import ModelTurn
from app.agents.tools.base import ToolContext
from app.agents.tools.doctor_registry import build_doctor_registry
from app.config import Settings


@pytest.fixture(autouse=True)
def _configured_backend_url(monkeypatch):
    """These tests exercise the real `BackendClient`, so it needs a
    non-empty `BACKEND_API_BASE_URL` to get past its own config check and
    reach the (mocked) `httpx.get` - unrelated to what's being tested
    here, so it's applied automatically for every test in this file."""

    monkeypatch.setattr(
        "app.agents.backend_client.settings",
        Settings(backend_api_base_url="http://backend.local", backend_api_timeout_seconds=8),
    )


def _text_turn(text: str) -> ModelTurn:
    return ModelTurn(
        text=text, function_calls=[],
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


def _multi_function_call_turn(calls: list[tuple[str, dict]]) -> ModelTurn:
    function_calls = [types.FunctionCall(name=n, args=a) for n, a in calls]
    parts = [types.Part(function_call=fc) for fc in function_calls]
    return ModelTurn(text=None, function_calls=function_calls, raw_content=types.Content(role="model", parts=parts))


def _mock_httpx_get_router(responses: dict[str, dict]) -> MagicMock:
    """Builds a mock for `httpx.get` that returns a canned JSON body based
    on a substring of the requested URL, so one test can stub several
    different backend endpoints at once."""

    def _side_effect(url, headers=None, params=None, timeout=None):
        for url_substring, body in responses.items():
            if url_substring in url:
                resp = MagicMock()
                resp.status_code = 200
                resp.json.return_value = body
                return resp
        raise AssertionError(f"Unexpected backend URL in test: {url}")

    mock = MagicMock(side_effect=_side_effect)
    return mock


def test_gemini_requests_a_single_tool_and_gets_a_grounded_reply():
    gemini = MagicMock()
    gemini.generate.side_effect = [
        _function_call_turn("get_patient_risk", {"patient_id": "7"}),
        _text_turn("Patient 7 is currently High risk based on the latest check-in."),
    ]

    with patch(
        "app.agents.backend_client.httpx.get",
        _mock_httpx_get_router(
            {
                "/api/checkins/": {
                    "results": [
                        {
                            "id": 1, "checkin_date": "2026-09-01", "ai_risk_level": "high",
                            "ai_risk_score": 82.0, "ai_notes": "severe symptoms reported",
                            "ai_recommended_action": "Prompt physician review is recommended.",
                            "ai_notification_recipient": "physician",
                        }
                    ]
                },
            }
        ),
    ):
        agent = Agent("sys", build_doctor_registry(), gemini_client=gemini)
        result = agent.run(
            message="[Patient ID: 7] Is this patient high risk?",
            context=ToolContext(bearer_token="doctor-a-token"),
        )

    assert result.reply == "Patient 7 is currently High risk based on the latest check-in."
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "get_patient_risk"
    assert result.tool_calls[0].succeeded is True


def test_multiple_tool_calls_in_one_turn_all_execute_and_round_trip():
    gemini = MagicMock()
    gemini.generate.side_effect = [
        _multi_function_call_turn(
            [
                ("get_patient_medications", {"patient_id": "7"}),
                ("get_medication_adherence", {"patient_id": "7"}),
            ]
        ),
        _text_turn("Summary: 1 active medication, adherence is partially adherent."),
    ]

    with patch(
        "app.agents.backend_client.httpx.get",
        _mock_httpx_get_router(
            {
                "/api/medications/": {
                    "results": [
                        {"id": 1, "name": "Metformin", "dosage": "500mg", "frequency": "twice_daily",
                         "instructions": "", "start_date": "2026-01-01", "end_date": None,
                         "is_active": True, "prescribed_by_name": "Dr. Sharma"}
                    ]
                },
                "/ai-summary/": {
                    "history": {"medication_adherence": {"overall_status": "partially_adherent"}}
                },
            }
        ),
    ):
        agent = Agent("sys", build_doctor_registry(), gemini_client=gemini)
        result = agent.run(
            message="[Patient ID: 7] Give me a clinical summary.",
            context=ToolContext(bearer_token="doctor-a-token"),
        )

    assert result.reply == "Summary: 1 active medication, adherence is partially adherent."
    assert {tc.tool_name for tc in result.tool_calls} == {
        "get_patient_medications",
        "get_medication_adherence",
    }
    assert all(tc.succeeded for tc in result.tool_calls)

    # Tool results were sent back to Gemini as function-response parts
    # before it produced the final answer (this is what "tool results are
    # correctly returned to Gemini" means concretely).
    second_call_contents = gemini.generate.call_args_list[1].kwargs["contents"]
    function_response_parts = [
        part
        for content in second_call_contents
        for part in content.parts
        if getattr(part, "function_response", None) is not None
    ]
    assert len(function_response_parts) == 2
    returned_names = {p.function_response.name for p in function_response_parts}
    assert returned_names == {"get_patient_medications", "get_medication_adherence"}


def test_narrow_question_only_triggers_the_relevant_tool():
    """'Is this patient's medication adherence okay?' should call only the
    adherence tool - Gemini's own choice, not something the agent forces,
    but we can assert the *mechanism* supports calling just one tool and
    stopping there without the harness requiring every tool to fire."""

    gemini = MagicMock()
    gemini.generate.side_effect = [
        _function_call_turn("get_medication_adherence", {"patient_id": "7"}),
        _text_turn("Adherence is currently adherent - no concerns."),
    ]

    with patch(
        "app.agents.backend_client.httpx.get",
        _mock_httpx_get_router(
            {"/ai-summary/": {"history": {"medication_adherence": {"overall_status": "adherent"}}}}
        ),
    ):
        agent = Agent("sys", build_doctor_registry(), gemini_client=gemini)
        result = agent.run(
            message="[Patient ID: 7] Is this patient's medication adherence okay?",
            context=ToolContext(bearer_token="doctor-a-token"),
        )

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].tool_name == "get_medication_adherence"


def test_tool_failure_from_backend_denial_does_not_crash_the_turn():
    """A different doctor's token (or an unowned patient) makes the
    backend deny the call; the agent must report this to Gemini as a
    failed tool call, not raise out of the turn."""

    gemini = MagicMock()
    gemini.generate.side_effect = [
        _function_call_turn("get_patient_basic_info", {"patient_id": "999"}),
        _text_turn("I was not able to access that patient's information."),
    ]

    def _forbidden(url, headers=None, params=None, timeout=None):
        resp = MagicMock()
        resp.status_code = 403
        resp.text = "Forbidden"
        return resp

    with patch("app.agents.backend_client.httpx.get", side_effect=_forbidden):
        agent = Agent("sys", build_doctor_registry(), gemini_client=gemini)
        result = agent.run(
            message="[Patient ID: 999] Show me this patient's basic details.",
            context=ToolContext(bearer_token="doctor-b-token"),
        )

    assert result.reply == "I was not able to access that patient's information."
    assert result.tool_calls[0].succeeded is False
    assert "Unauthorized" in result.tool_calls[0].summary


def test_missing_bearer_token_fails_closed_before_any_backend_call():
    gemini = MagicMock()
    gemini.generate.side_effect = [
        _function_call_turn("get_patient_risk", {"patient_id": "7"}),
        _text_turn("I don't have authorization to look that up."),
    ]

    with patch("app.agents.backend_client.httpx.get") as mock_get:
        agent = Agent("sys", build_doctor_registry(), gemini_client=gemini)
        result = agent.run(
            message="[Patient ID: 7] What's the risk level?",
            context=ToolContext(bearer_token=None),
        )
        mock_get.assert_not_called()

    assert result.tool_calls[0].succeeded is False
