"""Minimal runtime configuration for the AI Engine, read from environment variables."""

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    app_name: str = "HealBytes AI Engine"
    model_version: str = os.getenv("AI_MODEL_VERSION", "rule-engine-v6")
    log_level: str = os.getenv("AI_LOG_LEVEL", "INFO")


settings = Settings()
