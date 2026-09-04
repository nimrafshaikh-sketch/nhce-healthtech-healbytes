"""HTTP client for calling the existing Django backend.

The AI Engine never connects to a database directly and never mints its
own credentials. Every call here forwards the caller's own bearer token
as-is, so the backend's existing authentication and RBAC make every access
decision exactly as they do for any other API client (including the real
frontend) - this client adds no authority of its own.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.agents.exceptions import ToolExecutionError, UnauthorizedError
from app.config import settings

logger = logging.getLogger(__name__)


class BackendClient:
    """Thin wrapper over the existing backend's REST API."""

    def __init__(self, base_url: str | None = None, timeout: float | None = None) -> None:
        raw_base_url = base_url if base_url is not None else settings.backend_api_base_url
        self._base_url = raw_base_url.rstrip("/")
        self._timeout = timeout if timeout is not None else settings.backend_api_timeout_seconds

    def get(
        self,
        path: str,
        *,
        bearer_token: str | None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """GET `path` on the backend, forwarding `bearer_token` as-is.

        `params`, when given, is passed straight to `httpx` as the query
        string (safely encoded) rather than callers hand-building one -
        used by Doctor Agent tools that need e.g. `?patient=<id>` or
        `?query=<free text>`.

        Raises `UnauthorizedError` if no token was supplied (fail closed -
        this client never falls back to an unauthenticated or elevated
        call) or if the backend itself rejects the token (its RBAC is
        surfaced, never bypassed or retried with different credentials).
        Raises `ToolExecutionError` for any other backend-side failure:
        missing configuration, network error, timeout, or non-2xx
        response.
        """

        # Checked in this order deliberately: whether a token was supplied
        # is a property of the caller, not of this deployment's config, so
        # it fails closed the same way regardless of whether the backend
        # URL happens to be configured.
        if not bearer_token:
            raise UnauthorizedError(
                "No bearer token was supplied for this request; the backend call was not made."
            )
        if not self._base_url:
            raise ToolExecutionError(
                "BACKEND_API_BASE_URL is not configured; cannot reach the existing backend."
            )

        url = f"{self._base_url}{path}"
        headers = {"Authorization": f"Bearer {bearer_token}"}
        try:
            response = httpx.get(url, headers=headers, params=params, timeout=self._timeout)
        except httpx.RequestError as exc:
            raise ToolExecutionError(f"Could not reach the backend at {url}: {exc}") from exc

        if response.status_code in (401, 403):
            raise UnauthorizedError(
                f"Backend rejected the request to {path} "
                f"(status {response.status_code}) - existing RBAC denied access."
            )
        if response.status_code >= 400:
            raise ToolExecutionError(
                f"Backend returned {response.status_code} for {path}: {response.text[:300]}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise ToolExecutionError(f"Backend response for {path} was not valid JSON.") from exc

    def post(
        self,
        path: str,
        *,
        bearer_token: str | None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """POST `path` on the backend, forwarding `bearer_token` as-is."""
        if not bearer_token:
            raise UnauthorizedError(
                "No bearer token was supplied for this request; the backend call was not made."
            )
        if not self._base_url:
            raise ToolExecutionError(
                "BACKEND_API_BASE_URL is not configured; cannot reach the existing backend."
            )

        url = f"{self._base_url}{path}"
        headers = {"Authorization": f"Bearer {bearer_token}", "Content-Type": "application/json"}
        try:
            response = httpx.post(url, headers=headers, json=json_data, params=params, timeout=self._timeout)
        except httpx.RequestError as exc:
            raise ToolExecutionError(f"Could not reach the backend at {url}: {exc}") from exc

        if response.status_code in (401, 403):
            raise UnauthorizedError(
                f"Backend rejected the request to {path} "
                f"(status {response.status_code}) - existing RBAC denied access."
            )
        if response.status_code >= 400:
            raise ToolExecutionError(
                f"Backend returned {response.status_code} for {path}: {response.text[:300]}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise ToolExecutionError(f"Backend response for {path} was not valid JSON.") from exc

    def patch(
        self,
        path: str,
        *,
        bearer_token: str | None,
        json_data: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """PATCH `path` on the backend, forwarding `bearer_token` as-is."""
        if not bearer_token:
            raise UnauthorizedError(
                "No bearer token was supplied for this request; the backend call was not made."
            )
        if not self._base_url:
            raise ToolExecutionError(
                "BACKEND_API_BASE_URL is not configured; cannot reach the existing backend."
            )

        url = f"{self._base_url}{path}"
        headers = {"Authorization": f"Bearer {bearer_token}", "Content-Type": "application/json"}
        try:
            response = httpx.patch(url, headers=headers, json=json_data, params=params, timeout=self._timeout)
        except httpx.RequestError as exc:
            raise ToolExecutionError(f"Could not reach the backend at {url}: {exc}") from exc

        if response.status_code in (401, 403):
            raise UnauthorizedError(
                f"Backend rejected the request to {path} "
                f"(status {response.status_code}) - existing RBAC denied access."
            )
        if response.status_code >= 400:
            raise ToolExecutionError(
                f"Backend returned {response.status_code} for {path}: {response.text[:300]}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise ToolExecutionError(f"Backend response for {path} was not valid JSON.") from exc

