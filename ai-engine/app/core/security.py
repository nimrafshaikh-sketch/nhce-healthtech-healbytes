"""Internal service-to-service authentication for backend-only AI Engine endpoints."""

import hmac
from typing import Optional

from fastapi import Header, HTTPException, status

from app.config import settings

INTERNAL_SERVICE_KEY_HEADER = "X-Internal-Service-Key"


def require_internal_service_key(
    x_internal_service_key: Optional[str] = Header(default=None, alias=INTERNAL_SERVICE_KEY_HEADER),
) -> None:
    """Validate the shared service secret when AI_ENGINE_INTERNAL_KEY is configured.

    When AI_ENGINE_INTERNAL_KEY is unset/blank (e.g. isolated unit tests or
    unconfigured local development), requests are permitted so existing test
    suites remain deterministic. Whenever configured, callers must present the
    exact matching key via the X-Internal-Service-Key header.
    """
    expected = settings.internal_service_key
    if not expected:
        return

    if not x_internal_service_key or not hmac.compare_digest(x_internal_service_key.strip(), expected):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing internal service key.",
        )

