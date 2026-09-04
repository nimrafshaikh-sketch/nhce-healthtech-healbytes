"""HTTP-level tests for POST /api/v1/agents/receptionist."""

from unittest.mock import patch

from app.agents.agent import AgentResult, ToolCallOutcome
from app.agents.exceptions import AgentError, GeminiAPIError, GeminiConfigError


def _payload(**overrides):
    payload = {
        "request_id": "rec-req-1",
        "message": "What appointments are scheduled for today?",
    }
    payload.update(overrides)
    return payload


@patch("app.agents.receptionist_routes.Agent")
def test_successful_receptionist_turn(mock_agent_cls, client):
    mock_agent_cls.return_value.run.return_value = AgentResult(
        reply="Today you have 2 appointments scheduled: Rahul Verma at 10:00 AM and Eleanor Vance at 2:00 PM.",
        tool_calls=[
            ToolCallOutcome("list_appointments", {}, True, "ok"),
        ],
    )

    response = client.post(
        "/api/v1/agents/receptionist",
        json=_payload(),
        headers={"Authorization": "Bearer receptionist-jwt-token"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "Today you have 2 appointments" in body["reply"]
    assert len(body["tool_calls"]) == 1
    assert body["tool_calls"][0]["tool_name"] == "list_appointments"


@patch("app.agents.receptionist_routes.Agent")
def test_receptionist_accepts_auth_token_in_body(mock_agent_cls, client):
    mock_agent_cls.return_value.run.return_value = AgentResult(
        reply="Dr. Sarah Chen is available.",
        tool_calls=[
            ToolCallOutcome("list_available_doctors", {}, True, "ok"),
        ],
    )

    response = client.post(
        "/api/v1/agents/receptionist",
        json=_payload(auth_token="receptionist-body-token"),
    )

    assert response.status_code == 200
    body = response.json()
    assert "Dr. Sarah Chen" in body["reply"]


@patch("app.agents.receptionist_routes.Agent")
def test_missing_auth_token_fails_with_401(mock_agent_cls, client):
    response = client.post(
        "/api/v1/agents/receptionist",
        json=_payload(),
    )

    assert response.status_code == 401
    mock_agent_cls.return_value.run.assert_not_called()


@patch("app.agents.receptionist_routes.Agent")
def test_maps_gemini_config_error_to_503(mock_agent_cls, client):
    mock_agent_cls.return_value.run.side_effect = GeminiConfigError("GEMINI_API_KEY is not set.")

    response = client.post(
        "/api/v1/agents/receptionist",
        json=_payload(),
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 503


@patch("app.agents.receptionist_routes.Agent")
def test_maps_gemini_api_error_to_502(mock_agent_cls, client):
    mock_agent_cls.return_value.run.side_effect = GeminiAPIError("Upstream Gemini rate limit.")

    response = client.post(
        "/api/v1/agents/receptionist",
        json=_payload(),
        headers={"Authorization": "Bearer token"},
    )

    assert response.status_code == 502
