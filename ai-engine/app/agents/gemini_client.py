"""Reusable Gemini client - the only place this codebase talks to Gemini.

Wraps the official `google-genai` SDK behind a narrow interface so the
rest of the agent foundation never imports `google.genai` directly. This
centralizes every Gemini failure mode (missing key, API error, malformed
response) in one place and keeps the SDK swappable later without touching
`app/agents/agent.py`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from app.agents.exceptions import (
    GeminiAPIError,
    GeminiConfigError,
    MalformedModelResponseError,
)
from app.config import settings

import time

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ModelTurn:
    """One normalized turn from Gemini: either a final text reply, or a
    request to call the tool(s) listed in `function_calls` - never both,
    matching how the underlying API actually responds."""

    text: str | None
    function_calls: list[types.FunctionCall]
    raw_content: types.Content


class GeminiClient:
    """Thin, typed wrapper around `google.genai.Client` for text and
    function-calling generation.

    The API key is validated lazily, on first real use - not at import or
    app-startup time - so the rest of the AI Engine (including its
    existing, unrelated endpoints) keeps working when `GEMINI_API_KEY` is
    absent; only a request that actually needs Gemini fails, cleanly.
    """

    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key
        self._model_override = model
        self._client: genai.Client | None = None

    @property
    def model(self) -> str:
        return self._model_override or settings.gemini_model

    @property
    def api_key(self) -> str:
        return self._api_key if self._api_key is not None else settings.gemini_api_key

    def _ensure_client(self) -> genai.Client:
        if not self.api_key:
            raise GeminiConfigError(
                "GEMINI_API_KEY is not set. Configure it via environment "
                "variables (see app/agents/README.md). It must never be "
                "hardcoded, committed, or exposed to the frontend."
            )
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def generate(
        self,
        *,
        system_instruction: str,
        contents: list[types.Content],
        tool_declarations: list[dict[str, Any]] | None = None,
    ) -> ModelTurn:
        """Run one Gemini call and return a normalized `ModelTurn`.

        Raises `GeminiConfigError` if unconfigured, `GeminiAPIError` if the
        call itself fails (network, auth, quota, 4xx/5xx), or
        `MalformedModelResponseError` if the response can't be safely
        interpreted (no candidates, empty content, or neither text nor a
        tool call).
        """

        client = self._ensure_client()
        tools = None
        if tool_declarations:
            tools = [
                types.Tool(
                    function_declarations=[
                        types.FunctionDeclaration(
                            name=decl["name"],
                            description=decl["description"],
                            parameters_json_schema=decl["parameters_json_schema"],
                        )
                        for decl in tool_declarations
                    ]
                )
            ]

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=tools,
        )

        max_attempts = 3
        response = None
        for attempt in range(max_attempts):
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                )
                break
            except genai_errors.APIError as exc:
                status_code = getattr(exc, "code", None)
                # Retry on transient errors (503 Unavailable, 500 Internal, 429 Rate Limit)
                if status_code in (429, 500, 503) and attempt < max_attempts - 1:
                    sleep_time = (2 ** attempt) * 0.75
                    logger.warning(
                        "Gemini API returned %s (%s). Retrying in %.2fs (attempt %d/%d)...",
                        status_code,
                        exc,
                        sleep_time,
                        attempt + 1,
                        max_attempts,
                    )
                    time.sleep(sleep_time)
                    continue
                raise GeminiAPIError(f"Gemini API call failed: {exc}") from exc
            except GeminiConfigError:
                raise
            except Exception as exc:  # noqa: BLE001 - network/SDK errors, wrapped uniformly
                raise GeminiAPIError(f"Unexpected error calling Gemini: {exc}") from exc

        return self._parse_response(response)

    @staticmethod
    def _parse_response(response: types.GenerateContentResponse) -> ModelTurn:
        if not response.candidates:
            raise MalformedModelResponseError("Gemini returned no candidates.")
        candidate_content = response.candidates[0].content
        if candidate_content is None or not candidate_content.parts:
            raise MalformedModelResponseError("Gemini returned an empty response.")

        function_calls = [
            part.function_call for part in candidate_content.parts if part.function_call
        ]
        if function_calls:
            return ModelTurn(
                text=None, function_calls=function_calls, raw_content=candidate_content
            )

        text = response.text
        if not text or not text.strip():
            raise MalformedModelResponseError(
                "Gemini returned neither text nor a tool call."
            )
        return ModelTurn(text=text, function_calls=[], raw_content=candidate_content)
