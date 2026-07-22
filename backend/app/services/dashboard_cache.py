"""Optional Redis TTL cache for dashboard aggregate payloads (Phase 6.5)."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Literal

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.redis_cache import (
    cache_get_json_async,
    cache_set_json_async,
    redis_cache_available,
)
from app.models.models import User
from app.schemas.schemas import DashboardMetrics
from app.services.dashboard_metrics import build_dashboard_metrics

CacheStatus = Literal["hit", "miss", "bypass"]

_KEY_PREFIX = "raginspector:dash"


def dashboard_cache_enabled() -> bool:
    return (
        bool(settings.DASHBOARD_METRICS_CACHE_ENABLED)
        and int(settings.DASHBOARD_METRICS_CACHE_TTL_SECONDS) > 0
        and redis_cache_available()
    )


def _dashboard_key(user_id: str, pipeline_id: str | None) -> str:
    pipe = pipeline_id or "_"
    return f"{_KEY_PREFIX}:metrics:{user_id}:{pipe}"


def _aggregate_key(kind: str, user_id: str, pipeline_id: str | None, *parts: str) -> str:
    pipe = pipeline_id or "_"
    suffix = ":".join(parts) if parts else ""
    base = f"{_KEY_PREFIX}:{kind}:{user_id}:{pipe}"
    return f"{base}:{suffix}" if suffix else base


async def get_or_set_json(
    key: str,
    factory: Callable[[], Awaitable[Any]],
    *,
    ttl_seconds: int | None = None,
) -> tuple[Any, CacheStatus]:
    """Return cached JSON payload or compute + store. Fail-open on Redis errors."""
    if not dashboard_cache_enabled():
        return await factory(), "bypass"

    ttl = (
        int(settings.DASHBOARD_METRICS_CACHE_TTL_SECONDS)
        if ttl_seconds is None
        else int(ttl_seconds)
    )
    hit = await cache_get_json_async(key)
    if hit is not None:
        return hit, "hit"

    value = await factory()
    await cache_set_json_async(key, value, ttl)
    return value, "miss"


async def get_dashboard_metrics_cached(
    db: AsyncSession,
    current_user: User,
    pipeline_id: str | None = None,
) -> tuple[DashboardMetrics, CacheStatus]:
    if not dashboard_cache_enabled():
        metrics = await build_dashboard_metrics(db, current_user, pipeline_id=pipeline_id)
        return metrics, "bypass"

    key = _dashboard_key(str(current_user.id), pipeline_id)
    hit = await cache_get_json_async(key)
    if hit is not None:
        return DashboardMetrics.model_validate(hit), "hit"

    metrics = await build_dashboard_metrics(db, current_user, pipeline_id=pipeline_id)
    await cache_set_json_async(
        key,
        metrics.model_dump(mode="json"),
        int(settings.DASHBOARD_METRICS_CACHE_TTL_SECONDS),
    )
    return metrics, "miss"


def timeseries_cache_key(
    user_id: str,
    pipeline_id: str | None,
    metric: str,
    days: int,
) -> str:
    return _aggregate_key("timeseries", user_id, pipeline_id, metric, str(days))


def failure_distribution_cache_key(user_id: str, pipeline_id: str | None) -> str:
    return _aggregate_key("failures", user_id, pipeline_id)


def latency_breakdown_cache_key(
    user_id: str,
    pipeline_id: str | None,
    days: int,
) -> str:
    return _aggregate_key("latency", user_id, pipeline_id, str(days))


def bm25_cache_key(user_id: str, pipeline_id: str | None) -> str:
    return _aggregate_key("bm25", user_id, pipeline_id)
