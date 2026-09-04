"""HTTP-level tests for POST /api/v1/agents/doctor.

`app.agents.doctor_routes.Agent` is patched so these tests never touch a
real Gemini API or backend - they verify request/response wiring, the
patient_id/authorization requirements specific to the Doctor Agent, and
the same exception -> HTTP status mapping proven generically in Phase 1's
`test_agents_routes.py`.
"""

from unittest.mock import patch

from app.agents.agent import AgentResult, ToolCallOutcome
from app.agents.exceptions import AgentError, GeminiAPIError, GeminiConfigError


def _payload(**overrides):
    payload = {
        "request_id": "doc-req-1",
        "message": "Give me a concise clinical summary for this patient.",
        "patient_id": "7",
    }
    payload.update(overrides)
    return payload


@patch("app.agents.doctor_routes.Agent")
def test_successful_turn_returns_reply_and_tool_trace(mock_agent_cls, client):
    mock_agent_cls.return_value.run.return_value = AgentResult(
        reply="Patient 7: 1 active medication, adherent, risk Low.",
        tool_calls=[
            ToolCallOutcome("get_patient_medications", {"patient_id": "7"}, True, "ok"),
            ToolCallOutcome("get_medication_adherence", {"patient_id": "7"}, True, "ok"),
            ToolCallOutcome("get_patient_risk", {"patient_id": "7"}, True, "ok"),
        ],
    )

    response = client.post(
        "/api/v1/agents/doctor", json=_payload(), headers={"Authorization": "Bearer doctor-token"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["reply"] == "Patient 7: 1 active medication, adherent, risk Low."
    assert len(body["tool_calls"]) == 3


@patch("app.agents.doctor_routes.Agent")
def test_patient_id_is_required(mock_agent_cls, client):
    response = client.post(
        "/api/v1/agents/doctor",
        json=_payload(patient_id=None),
        headers={"Authorization": "Bearer doctor-token"},
    )

    assert response.status_code == 422
    mock_agent_cls.return_value.run.assert_not_called()


@patch("app.agents.doctor_routes.Agent")
def test_missing_authorization_header_fails_closed_without_calling_gemini(mock_agent_cls, client):
    response = client.post("/api/v1/agents/doctor", json=_payload())

    assert response.status_code == 401
    mock_agent_cls.return_value.run.assert_not_called()


@patch("app.agents.doctor_routes.Agent")
def test_bearer_token_is_forwarded_into_tool_context(mock_agent_cls, client):
    mock_agent_cls.return_value.run.return_value = AgentResult(reply="ok", tool_calls=[])

    client.post(
        "/api/v1/agents/doctor", json=_payload(), headers={"Authorization": "Bearer abc123"}
    )

    _, kwargs = mock_agent_cls.return_value.run.call_args
    assert kwargs["context"].bearer_token == "abc123"


@patch("app.agents.doctor_routes.Agent")
def test_patient_id_is_embedded_in_the_message_sent_to_the_agent(mock_agent_cls, client):
    mock_agent_cls.return_value.run.return_value = AgentResult(reply="ok", tool_calls=[])

    client.post(
        "/api/v1/agents/doctor",
        json=_payload(patient_id="42", message="How is this patient doing?"),
        headers={"Authorization": "Bearer abc123"},
    )

    _, kwargs = mock_agent_cls.return_value.run.call_args
    assert "42" in kwargs["message"]
    assert "How is this patient doing?" in kwargs["message"]


@patch("app.agents.doctor_routes.Agent")
def test_missing_gemini_api_key_returns_503(mock_agent_cls, client):
    mock_agent_cls.return_value.run.side_effect = GeminiConfigError("GEMINI_API_KEY is not set.")

    response = client.post(
        "/api/v1/agents/doctor", json=_payload(), headers={"Authorization": "Bearer doctor-token"}
    )

    assert response.status_code == 503


@patch("app.agents.doctor_routes.Agent")
def test_gemini_api_failure_returns_502(mock_agent_cls, client):
    mock_agent_cls.return_value.run.side_effect = GeminiAPIError("upstream failure")

    response = client.post(
        "/api/v1/agents/doctor", json=_payload(), headers={"Authorization": "Bearer doctor-token"}
    )

    assert response.status_code == 502


@patch("app.agents.doctor_routes.Agent")
def test_generic_agent_error_returns_500(mock_agent_cls, client):
    mock_agent_cls.return_value.run.side_effect = AgentError("iteration limit exceeded")

    response = client.post(
        "/api/v1/agents/doctor", json=_payload(), headers={"Authorization": "Bearer doctor-token"}
    )

    assert response.status_code == 500


def test_response_never_includes_the_bearer_token_or_api_key(client):
    with patch("app.agents.doctor_routes.Agent") as mock_agent_cls:
        mock_agent_cls.return_value.run.return_value = AgentResult(reply="ok", tool_calls=[])
        response = client.post(
            "/api/v1/agents/doctor",
            json=_payload(),
            headers={"Authorization": "Bearer super-secret-token"},
        )

    assert "super-secret-token" not in response.text
