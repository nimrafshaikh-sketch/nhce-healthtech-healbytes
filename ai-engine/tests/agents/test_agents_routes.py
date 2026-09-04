"""HTTP-level tests for POST /api/v1/agents/patient-summary.

`app.agents.routes.Agent` is patched so these tests never touch a real
Gemini API or backend - they verify request/response wiring and the
exception -> HTTP status mapping described in the project instructions
(missing key, Gemini failure, invalid/failed tool call, malformed
response).
"""

from unittest.mock import MagicMock, patch

from app.agents.agent import AgentResult, ToolCallOutcome
from app.agents.exceptions import (
    AgentError,
    GeminiAPIError,
    GeminiConfigError,
    MalformedModelResponseError,
)


def _payload(**overrides):
    payload = {"request_id": "req-1", "message": "What is patient 7's basic info?"}
    payload.update(overrides)
    return payload


@patch("app.agents.routes.Agent")
def test_successful_turn_returns_reply_and_tool_trace(mock_agent_cls, client):
    mock_agent_cls.return_value.run.return_value = AgentResult(
        reply="Patient 7 is Jane Doe.",
        tool_calls=[
            ToolCallOutcome(
                tool_name="get_patient_basic_info",
                arguments={"patient_id": "7"},
                succeeded=True,
                summary="'get_patient_basic_info' completed successfully.",
            )
        ],
    )

    response = client.post(
        "/api/v1/agents/patient-summary",
        json=_payload(),
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Patient 7 is Jane Doe."
    assert body["tool_calls"][0]["tool_name"] == "get_patient_basic_info"
    assert body["tool_calls"][0]["succeeded"] is True


@patch("app.agents.routes.Agent")
def test_bearer_token_is_forwarded_into_tool_context(mock_agent_cls, client):
    mock_agent_cls.return_value.run.return_value = AgentResult(reply="ok", tool_calls=[])

    client.post(
        "/api/v1/agents/patient-summary",
        json=_payload(),
        headers={"Authorization": "Bearer abc123"},
    )

    _, kwargs = mock_agent_cls.return_value.run.call_args
    assert kwargs["context"].bearer_token == "abc123"


@patch("app.agents.routes.Agent")
def test_missing_authorization_header_still_runs_with_no_token(mock_agent_cls, client):
    mock_agent_cls.return_value.run.return_value = AgentResult(reply="ok", tool_calls=[])

    response = client.post("/api/v1/agents/patient-summary", json=_payload())

    assert response.status_code == 200
    _, kwargs = mock_agent_cls.return_value.run.call_args
    assert kwargs["context"].bearer_token is None


@patch("app.agents.routes.Agent")
def test_missing_gemini_api_key_returns_503(mock_agent_cls, client):
    mock_agent_cls.return_value.run.side_effect = GeminiConfigError("GEMINI_API_KEY is not set.")

    response = client.post("/api/v1/agents/patient-summary", json=_payload())

    assert response.status_code == 503


@patch("app.agents.routes.Agent")
def test_gemini_api_failure_returns_502(mock_agent_cls, client):
    mock_agent_cls.return_value.run.side_effect = GeminiAPIError("upstream failure")

    response = client.post("/api/v1/agents/patient-summary", json=_payload())

    assert response.status_code == 502


@patch("app.agents.routes.Agent")
def test_malformed_model_response_returns_502(mock_agent_cls, client):
    mock_agent_cls.return_value.run.side_effect = MalformedModelResponseError("bad response")

    response = client.post("/api/v1/agents/patient-summary", json=_payload())

    assert response.status_code == 502


@patch("app.agents.routes.Agent")
def test_generic_agent_error_returns_500(mock_agent_cls, client):
    mock_agent_cls.return_value.run.side_effect = AgentError("iteration limit exceeded")

    response = client.post("/api/v1/agents/patient-summary", json=_payload())

    assert response.status_code == 500


def test_rejects_malformed_payload(client):
    response = client.post("/api/v1/agents/patient-summary", json={"message": "no request_id"})

    assert response.status_code == 422
