"""Centralized exception handling for the AI Engine API."""

import logging

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Attach a clean, consistent error response for request validation failures.

    Uses `jsonable_encoder` (not raw `exc.errors()`) because a `ValueError`
    raised from a Pydantic `model_validator` — e.g. the "insufficient data"
    check in `AIAnalysisRequest` — puts the actual, non-JSON-serializable
    exception object in each error's `ctx["error"]` field; `jsonable_encoder`
    safely stringifies it instead of the response serializer crashing.
    """

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = jsonable_encoder(exc.errors())
        logger.warning("Validation error on %s: %s", request.url.path, errors)
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": "Invalid request payload.", "errors": errors},
        )
