"""Minimal runtime configuration for the AI Engine, read from environment variables."""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv(override=True)


@dataclass(frozen=True)
class Settings:
    app_name: str = "HealBytes AI Engine"
    api_prefix: str = "/api/v1"
    model_version: str = os.getenv("AI_MODEL_VERSION", "0.0.0-unimplemented")
    log_level: str = os.getenv("AI_LOG_LEVEL", "INFO")

    # --- Agent foundation (Gemini reasoning layer) ---
    # Never hardcode a key: it must come from the environment, and it is
    # never read by, or exposed to, the frontend. An empty default is
    # intentional - `GeminiClient` validates presence lazily (on first use)
    # so the rest of the service still runs when the key is absent.
    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")

    @property
    def gemini_model(self) -> str:
        return os.getenv("GEMINI_MODEL", "gemini-3.1-flash-lite")

    @property
    def agent_max_tool_iterations(self) -> int:
        return int(os.getenv("AGENT_MAX_TOOL_ITERATIONS", "4"))

    # --- Existing Django backend (source of truth for data + auth/RBAC) ---
    # Tools call this over HTTP only; the AI Engine never touches the
    # database directly and never mints or bypasses auth - it forwards the
    # caller's own bearer token.
    backend_api_base_url: str = os.getenv("BACKEND_API_BASE_URL", "")
    backend_api_timeout_seconds: float = float(os.getenv("BACKEND_API_TIMEOUT_SECONDS", "8"))


settings = Settings()
