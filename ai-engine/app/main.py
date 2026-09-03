"""FastAPI application entry point for the HealBytes AI Engine.

This service is Phase 0: it exposes and validates the AI request/response
contract only. No risk-scoring, ML, or backend logic lives here.
"""

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.history.routes import router as history_router

configure_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.model_version,
    description=(
        "AI Engine contract foundation for patient check-in analysis. "
        "Phase 0: request/response contract and validation only."
    ),
)

register_exception_handlers(app)
app.include_router(router, prefix=settings.api_prefix)
app.include_router(history_router, prefix=settings.api_prefix)
