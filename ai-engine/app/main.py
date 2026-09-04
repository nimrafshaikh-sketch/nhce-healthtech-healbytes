"""FastAPI application entry point for the HealBytes AI Engine.

This service is Phase 0: it exposes and validates the AI request/response
contract only. No risk-scoring, ML, or backend logic lives here.
"""

from fastapi import FastAPI

from app.agents.doctor_routes import router as doctor_agent_router
from app.agents.receptionist_routes import router as receptionist_agent_router
from app.agents.routes import router as agents_router
from app.api.routes import router
from app.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.history.routes import router as history_router

from fastapi.middleware.cors import CORSMiddleware

configure_logging()

app = FastAPI(
    title=settings.app_name,
    version=settings.model_version,
    description=(
        "AI Engine contract foundation for patient check-in analysis. "
        "Phase 0: request/response contract and validation only."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(router, prefix=settings.api_prefix)
app.include_router(history_router, prefix=settings.api_prefix)
# Shared Gemini + agent foundation (see app/agents/README.md). Independent
# of the deterministic /analyze and /history/summary pipelines above -
# calling it never affects, and is never required by, either of them.
app.include_router(agents_router, prefix=settings.api_prefix)
# Doctor Agent (Phase 2, see app/agents/doctor_routes.py) - a role-specific
# agent built on the same foundation, with its own tools/system instruction.
app.include_router(doctor_agent_router, prefix=settings.api_prefix)
# Receptionist Agent (Front-desk assistance & appointment coordination).
app.include_router(receptionist_agent_router, prefix=settings.api_prefix)
