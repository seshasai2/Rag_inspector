import logging
import uuid

import structlog

from app.core.config import settings


def setup_logging() -> None:
    """Configure structlog (JSON in production). Safe to call more than once.

    Bound context fields used across API / workers:
    - request_id / correlation_id / trace_id / error_id
    - task_id (Celery)
    """
    production = settings.ENVIRONMENT.lower() == "production"
    level_name = (getattr(settings, "LOG_LEVEL", None) or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
    ]
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.JSONRenderer() if production else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def new_error_id() -> str:
    return f"err_{uuid.uuid4().hex[:16]}"


def new_trace_id() -> str:
    return f"trc_{uuid.uuid4().hex}"
