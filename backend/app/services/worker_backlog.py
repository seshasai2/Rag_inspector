"""Celery / analysis backlog metrics for ops (Phase 6.6)."""

from __future__ import annotations

from typing import Any, Optional

from redis import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import AnalysisJob, JobStatus, QueryTrace

# Queues declared in ``app.workers.celery_app`` task_routes
CELERY_QUEUES = ("analysis", "celery")


def redis_queue_depths(
    redis_url: str | None = None,
    queues: tuple[str, ...] = CELERY_QUEUES,
) -> dict[str, Optional[int]]:
    """Return LLEN for each Celery Redis list key. ``None`` if Redis unreachable."""
    url = redis_url or settings.REDIS_URL
    depths: dict[str, Optional[int]] = {q: None for q in queues}
    try:
        client = Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        try:
            client.ping()
            for q in queues:
                depths[q] = int(client.llen(q))
        finally:
            client.close()
    except Exception:
        pass
    return depths


async def analysis_job_counts(db: AsyncSession) -> dict[str, int]:
    """Counts of ``analysis_jobs`` by status."""
    result = await db.execute(select(AnalysisJob.status, func.count()).group_by(AnalysisJob.status))
    counts = {s.value: 0 for s in JobStatus}
    for status, n in result.all():
        key = status.value if hasattr(status, "value") else str(status)
        counts[key] = int(n or 0)
    return counts


async def trace_analysis_status_counts(db: AsyncSession) -> dict[str, int]:
    """App-level backlog: traces still pending / analyzing."""
    result = await db.execute(
        select(QueryTrace.analysis_status, func.count())
        .where(QueryTrace.analysis_status.in_(("pending", "analyzing", "failed")))
        .group_by(QueryTrace.analysis_status)
    )
    out = {"pending": 0, "analyzing": 0, "failed": 0}
    for status, n in result.all():
        if status in out:
            out[str(status)] = int(n or 0)
    return out


async def collect_backlog_snapshot(db: AsyncSession) -> dict[str, Any]:
    """JSON-friendly backlog snapshot for ``/ops/backlog``."""
    queue_depths = redis_queue_depths()
    jobs = await analysis_job_counts(db)
    traces = await trace_analysis_status_counts(db)
    redis_ok = any(v is not None for v in queue_depths.values())
    pending_jobs = int(jobs.get("pending", 0))
    running_jobs = int(jobs.get("running", 0))
    redis_waiting = sum(v or 0 for v in queue_depths.values())
    return {
        "redis_ok": redis_ok,
        "celery_queue_depths": queue_depths,
        "celery_messages_waiting": redis_waiting if redis_ok else None,
        "analysis_jobs": jobs,
        "trace_analysis_status": traces,
        "backlog_pending_or_running": pending_jobs + running_jobs,
    }


def render_prometheus_backlog_lines(snapshot: dict[str, Any]) -> list[str]:
    """Prometheus text exposition lines for backlog gauges."""
    lines: list[str] = [
        "# HELP raginspector_celery_queue_depth Redis list length for a Celery queue",
        "# TYPE raginspector_celery_queue_depth gauge",
    ]
    depths = snapshot.get("celery_queue_depths") or {}
    for name, depth in depths.items():
        if depth is None:
            continue
        lines.append(f'raginspector_celery_queue_depth{{queue="{name}"}} {int(depth)}')

    lines.extend(
        [
            "# HELP raginspector_analysis_jobs AnalysisJob rows by status",
            "# TYPE raginspector_analysis_jobs gauge",
        ]
    )
    for status, n in (snapshot.get("analysis_jobs") or {}).items():
        lines.append(f'raginspector_analysis_jobs{{status="{status}"}} {int(n)}')

    lines.extend(
        [
            "# HELP raginspector_trace_analysis Trace rows by analysis_status (active backlog)",
            "# TYPE raginspector_trace_analysis gauge",
        ]
    )
    for status, n in (snapshot.get("trace_analysis_status") or {}).items():
        lines.append(f'raginspector_trace_analysis{{status="{status}"}} {int(n)}')

    lines.extend(
        [
            "# HELP raginspector_analysis_backlog Pending + running AnalysisJob count",
            "# TYPE raginspector_analysis_backlog gauge",
            f"raginspector_analysis_backlog {int(snapshot.get('backlog_pending_or_running') or 0)}",
        ]
    )
    return lines
