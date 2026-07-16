"""Enqueue RAG analysis jobs with clear failure semantics when workers are down."""

from __future__ import annotations

import structlog
from structlog.contextvars import get_contextvars

logger = structlog.get_logger()

QUEUE_UNAVAILABLE_MESSAGE = (
    "Analysis worker unavailable (Redis/Celery). "
    "Trace was stored. Retry with POST /api/v1/queries/{trace_id}/reanalyze "
    "after starting celery_worker."
)


def enqueue_analysis(trace_id: str) -> str | None:
    """Attempt to queue ``run_analysis``. Returns Celery task id or ``None``."""
    from app.workers.tasks import run_analysis

    headers: dict[str, str] = {}
    request_id = get_contextvars().get("request_id")
    if request_id:
        headers["request_id"] = str(request_id)

    try:
        if headers:
            task = run_analysis.apply_async(args=[trace_id], headers=headers)
        else:
            task = run_analysis.delay(trace_id)
        return getattr(task, "id", None)
    except Exception as exc:
        logger.warning(
            "Failed to enqueue analysis task",
            error=str(exc),
            trace_id=trace_id,
        )
        return None


def queue_unavailable_message(trace_id: str) -> str:
    return QUEUE_UNAVAILABLE_MESSAGE.format(trace_id=trace_id)
