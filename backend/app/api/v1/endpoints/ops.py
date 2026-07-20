import secrets
import time
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from redis import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_db
from app.experimental import experimental_manifest
from app.services.worker_backlog import collect_backlog_snapshot, render_prometheus_backlog_lines

router = APIRouter()
STARTED_AT = time.time()


def require_ops_token(x_ops_token: str | None = Header(default=None, alias="X-Ops-Token")) -> None:
    """Gate non-probe ops endpoints when OPS_SHARED_TOKEN is configured."""
    expected = (settings.OPS_SHARED_TOKEN or "").strip()
    if not expected:
        return
    if not x_ops_token or not secrets.compare_digest(x_ops_token, expected):
        raise HTTPException(status_code=401, detail="Invalid or missing X-Ops-Token")


@router.get("/experimental")
async def experimental_surfaces(_: None = Depends(require_ops_token)):
    """Honesty manifest for partial/stub product surfaces (ops / internal)."""
    return {
        "surfaces": experimental_manifest(),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/ready")
async def readiness(db: AsyncSession = Depends(get_db)):
    """Readiness probe — HTTP 503 when DB or Redis is down (Compose/K8s healthchecks).

    Soft checks (workers/backlog/migrations) are reported but do not fail the probe
    unless hard deps (database, redis) fail.
    """
    checks: dict[str, str] = {"database": "unknown", "redis": "unknown"}
    soft: dict[str, str] = {}

    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception as exc:
        # Include a short message so cloud misconfig (sslmode/asyncpg) is diagnosable.
        detail = str(exc).replace("\n", " ")[:160]
        checks["database"] = f"error: {exc.__class__.__name__}: {detail}"

    try:
        redis_client = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        )
        try:
            redis_client.ping()
            checks["redis"] = "ok"
        finally:
            redis_client.close()
    except Exception as exc:
        detail = str(exc).replace("\n", " ")[:120]
        checks["redis"] = f"error: {exc.__class__.__name__}: {detail}"

    # Soft: alembic version present (schema applied)
    try:
        result = await db.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
        version = result.scalar_one_or_none()
        soft["migrations"] = f"ok:{version}" if version else "missing"
    except Exception as exc:
        detail = str(exc).replace("\n", " ")[:120]
        soft["migrations"] = f"error: {exc.__class__.__name__}: {detail}"
    # Soft: analysis backlog snapshot (also exercises Redis broker when Celery is used)
    try:
        snapshot = await collect_backlog_snapshot(db)
        jobs = snapshot.get("analysis_jobs") or {}
        pending = int(jobs.get("pending") or 0)
        running = int(jobs.get("running") or 0)
        soft["analysis_backlog"] = f"pending={pending},running={running}"
        soft["celery_queues"] = (
            "ok" if snapshot.get("redis_ok") or snapshot.get("celery_queue_depths") else "unknown"
        )
    except Exception as exc:
        soft["analysis_backlog"] = f"error: {exc.__class__.__name__}"

    healthy = all(value == "ok" for value in checks.values())
    body = {
        "status": "ready" if healthy else "degraded",
        "checks": checks,
        "soft_checks": soft,
        "version": "1.0.0",
        "environment": settings.ENVIRONMENT,
        "uptime_seconds": round(max(time.time() - STARTED_AT, 0)),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    return JSONResponse(status_code=200 if healthy else 503, content=body)


@router.get("/backlog")
async def analysis_backlog(
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_ops_token),
):
    """Celery queue depths + analysis job/trace backlog (Phase 6.6)."""
    snapshot = await collect_backlog_snapshot(db)
    return {
        **snapshot,
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "guidance": "docs/WORKER.md",
    }


@router.get("/metrics")
async def metrics(
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    """Prometheus scrape endpoint — intentionally ungated on private networks.

    Protect at the edge (network policy / Nginx allowlist). Sensitive ops
    surfaces (``/backlog``, ``/experimental``) still require ``X-Ops-Token``.
    """
    from app.core.http_metrics import render_http_metrics_lines
    from app.core.jwt_denylist import render_denylist_metrics_lines

    uptime = max(time.time() - STARTED_AT, 0)
    lines = [
        "# HELP raginspector_api_uptime_seconds API process uptime in seconds",
        "# TYPE raginspector_api_uptime_seconds gauge",
        f"raginspector_api_uptime_seconds {uptime:.0f}",
        "# HELP raginspector_build_info Static application build info",
        "# TYPE raginspector_build_info gauge",
        f'raginspector_build_info{{environment="{settings.ENVIRONMENT}"}} 1',
    ]
    lines.extend(render_http_metrics_lines())
    lines.extend(render_denylist_metrics_lines())
    try:
        snapshot = await collect_backlog_snapshot(db)
        lines.extend(render_prometheus_backlog_lines(snapshot))
    except Exception:
        lines.extend(
            [
                "# HELP raginspector_analysis_backlog Pending + running AnalysisJob count",
                "# TYPE raginspector_analysis_backlog gauge",
                "raginspector_analysis_backlog 0",
            ]
        )
    lines.append("")
    # Must be plain text — returning a bare str makes FastAPI JSON-encode it,
    # which breaks Prometheus scrapes (Content-Type application/json, up=0).
    return PlainTextResponse(
        content="\n".join(lines),
        media_type="text/plain; version=0.0.4; charset=utf-8",
    )
