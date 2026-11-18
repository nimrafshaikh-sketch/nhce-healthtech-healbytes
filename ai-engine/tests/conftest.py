"""Shared pytest fixtures for AI Engine tests."""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(autouse=True)
def _isolate_internal_service_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep unit tests isolated from container runtime AI_ENGINE_INTERNAL_KEY unless explicitly set."""
    monkeypatch.delenv("AI_ENGINE_INTERNAL_KEY", raising=False)


@pytest.fixture()
def client() -> TestClient:
    return TestClient(app)
