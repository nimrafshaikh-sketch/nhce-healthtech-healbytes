"""FastAPI application entry point for the HealBytes AI Engine.

Routes are mounted at the application root (no version prefix): the agreed
backend contract calls `POST {AI_ENGINE_URL}/analyze/` directly — see
`app/api/routes.py`.
"""

from fastapi import FastAPI

from app.api.routes import router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging

configure_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.model_version,
    description=(
        "AI Engine for patient check-in risk analysis. Deterministic, "
        "rule-based baseline — see README.md for the full pipeline and "
        "the agreed request/response contract."
    ),
)

register_exception_handlers(app)
app.include_router(router)
