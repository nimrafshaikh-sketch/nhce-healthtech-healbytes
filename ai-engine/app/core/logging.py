"""Minimal logging configuration for the AI Engine."""

import logging

from app.config import settings


def configure_logging() -> None:
    """Configure root logging once at application startup."""

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
