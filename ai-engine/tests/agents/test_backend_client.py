"""Tests for `app/agents/backend_client.py`. `httpx.get` is mocked - no
real backend needs to be running.
"""

from unittest.mock import MagicMock, patch

import httpx
import pytest

from app.agents.backend_client import BackendClient
from app.agents.exceptions import ToolExecutionError, UnauthorizedError


def test_missing_base_url_raises_tool_execution_error():
    client = BackendClient(base_url="", timeout=1)
    with pytest.raises(ToolExecutionError):
        client.get("/api/patients/1/", bearer_token="tok")


def test_missing_bearer_token_raises_unauthorized_without_calling_backend():
    client = BackendClient(base_url="http://backend.local", timeout=1)
    with patch("app.agents.backend_client.httpx.get") as mock_get:
        with pytest.raises(UnauthorizedError):
            client.get("/api/patients/1/", bearer_token=None)
        mock_get.assert_not_called()


@patch("app.agents.backend_client.httpx.get")
def test_successful_get_returns_json_and_forwards_token(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"id": 1, "full_name": "Jane Doe"}
    mock_get.return_value = mock_response

    client = BackendClient(base_url="http://backend.local", timeout=1)
    result = client.get("/api/patients/1/", bearer_token="abc123")

    assert result == {"id": 1, "full_name": "Jane Doe"}
    _, kwargs = mock_get.call_args
    assert kwargs["headers"]["Authorization"] == "Bearer abc123"


@pytest.mark.parametrize("status_code", [401, 403])
@patch("app.agents.backend_client.httpx.get")
def test_backend_rejection_raises_unauthorized(mock_get, status_code):
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_get.return_value = mock_response

    client = BackendClient(base_url="http://backend.local", timeout=1)
    with pytest.raises(UnauthorizedError):
        client.get("/api/patients/1/", bearer_token="abc123")


@patch("app.agents.backend_client.httpx.get")
def test_backend_5xx_raises_tool_execution_error(mock_get):
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "internal error"
    mock_get.return_value = mock_response

    client = BackendClient(base_url="http://backend.local", timeout=1)
    with pytest.raises(ToolExecutionError):
        client.get("/api/patients/1/", bearer_token="abc123")


@patch("app.agents.backend_client.httpx.get")
def test_network_error_raises_tool_execution_error(mock_get):
    mock_get.side_effect = httpx.ConnectError("connection refused")

    client = BackendClient(base_url="http://backend.local", timeout=1)
    with pytest.raises(ToolExecutionError):
        client.get("/api/patients/1/", bearer_token="abc123")
