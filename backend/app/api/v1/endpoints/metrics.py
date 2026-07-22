from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_min_plan
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.db.session import get_db
from app.models.models import Pipeline, QueryTrace, User
from app.services.bm25_metrics import build_bm25_aggregate
from app.services.dashboard_cache import (
    bm25_cache_key,
    failure_distribution_cache_key,
    get_dashboard_metrics_cached,
    get_or_set_json,
    latency_breakdown_cache_key,
    timeseries_cache_key,
)

router = APIRouter()

_BM25_PLAN = FEATURE_MIN_PLAN["bm25_comparison"]


def _set_cache_header(response: Response, status: str) -> None:
    response.headers["X-Cache"] = status


@router.get("/dashboard")
async def get_dashboard_metrics(
    response: Response,
    pipeline_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    metrics, cache_status = await get_dashboard_metrics_cached(
        db,
        current_user,
        pipeline_id=str(pipeline_id) if pipeline_id else None,
    )
    _set_cache_header(response, cache_status)
    return metrics


@router.get("/timeseries")
async def get_timeseries(
    response: Response,
    metric: str = Query("faithfulness_score"),
    pipeline_id: Optional[UUID] = Query(None),
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    valid_metrics = [
        "faithfulness_score",
        "context_precision_score",
        "context_recall_score",
        "grounded_fraction",
        "answer_relevance_score",
        "trustworthiness_score",
    ]
    if metric not in valid_metrics:
        metric = "faithfulness_score"

    pipe = str(pipeline_id) if pipeline_id else None
    key = timeseries_cache_key(str(current_user.id), pipe, metric, days)

    async def _compute():
        pipelines_result = await db.execute(
            select(Pipeline.id).where(Pipeline.user_id == current_user.id)
        )
        pipeline_ids = list(pipelines_result.scalars().all())
        if not pipeline_ids:
            return {"metric": metric, "data": []}

        metric_col = getattr(QueryTrace, metric)
        filters = [QueryTrace.pipeline_id.in_(pipeline_ids)]
        if pipeline_id:
            filters.append(QueryTrace.pipeline_id == pipeline_id)
        filters.append(QueryTrace.traced_at >= datetime.now(timezone.utc) - timedelta(days=days))

        # Aggregate in Python — Postgres date_trunc GROUP BY was hanging the sole
        # uvicorn worker on Render Free (~50s → 502), taking down /health with it.
        result = await db.execute(
            select(QueryTrace.traced_at, metric_col).where(and_(*filters))
        )
        buckets: dict[str, list[float]] = {}
        for traced_at, val in result.all():
            if traced_at is None:
                continue
            day = (
                traced_at
                if isinstance(traced_at, str)
                else traced_at.strftime("%Y-%m-%d")
            )
            if isinstance(day, str) and len(day) >= 10:
                day = day[:10]
            buckets.setdefault(day, []).append(float(val or 0))

        data = [
            {
                "date": day,
                "value": round(sum(values) / len(values), 3),
                "count": len(values),
            }
            for day, values in sorted(buckets.items())
        ]
        return {"metric": metric, "data": data}

    payload, cache_status = await get_or_set_json(key, _compute)
    _set_cache_header(response, cache_status)
    return payload


@router.get("/bm25-comparison")
async def get_bm25_comparison_metrics(
    response: Response,
    pipeline_id: Optional[UUID] = Query(None),
    current_user: User = Depends(require_min_plan(_BM25_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    """PRD F4 aggregate: share of traces where BM25 outperforms vector."""
    pipe = str(pipeline_id) if pipeline_id else None
    key = bm25_cache_key(str(current_user.id), pipe)

    async def _compute():
        return await build_bm25_aggregate(
            db,
            current_user,
            pipeline_id=pipe,
        )

    payload, cache_status = await get_or_set_json(key, _compute)
    _set_cache_header(response, cache_status)
    return payload


@router.get("/failure-distribution")
async def get_failure_distribution(
    response: Response,
    pipeline_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pipe = str(pipeline_id) if pipeline_id else None
    key = failure_distribution_cache_key(str(current_user.id), pipe)

    async def _compute():
        pipelines_result = await db.execute(
            select(Pipeline.id).where(Pipeline.user_id == current_user.id)
        )
        pipeline_ids = list(pipelines_result.scalars().all())
        if not pipeline_ids:
            return {"data": []}

        filters = [QueryTrace.pipeline_id.in_(pipeline_ids), QueryTrace.failure_type != None]
        if pipeline_id:
            filters.append(QueryTrace.pipeline_id == pipeline_id)

        result = await db.execute(
            select(QueryTrace.failure_type, func.count(QueryTrace.id))
            .where(and_(*filters))
            .group_by(QueryTrace.failure_type)
        )
        data = [
            {
                "failure_type": row[0].value if hasattr(row[0], "value") else str(row[0]),
                "count": row[1],
            }
            for row in result.all()
        ]
        return {"data": data}

    payload, cache_status = await get_or_set_json(key, _compute)
    _set_cache_header(response, cache_status)
    return payload


@router.get("/latency-breakdown")
async def get_latency_breakdown(
    response: Response,
    pipeline_id: Optional[UUID] = Query(None),
    days: int = Query(30, ge=1, le=90),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pipe = str(pipeline_id) if pipeline_id else None
    key = latency_breakdown_cache_key(str(current_user.id), pipe, days)

    async def _compute():
        pipelines_result = await db.execute(
            select(Pipeline.id).where(Pipeline.user_id == current_user.id)
        )
        pipeline_ids = list(pipelines_result.scalars().all())
        if not pipeline_ids:
            return {"data": []}

        filters = [
            QueryTrace.pipeline_id.in_(pipeline_ids),
            QueryTrace.traced_at >= datetime.now(timezone.utc) - timedelta(days=days),
        ]
        if pipeline_id:
            filters.append(QueryTrace.pipeline_id == pipeline_id)

        # Same as timeseries: avoid Postgres date_trunc GROUP BY on Render Free.
        result = await db.execute(
            select(
                QueryTrace.traced_at,
                QueryTrace.embed_latency_ms,
                QueryTrace.retrieve_latency_ms,
                QueryTrace.generate_latency_ms,
            ).where(and_(*filters))
        )
        buckets: dict[str, list[tuple[float, float, float]]] = {}
        for traced_at, embed, retrieve, generate in result.all():
            if traced_at is None:
                continue
            day = (
                traced_at
                if isinstance(traced_at, str)
                else traced_at.strftime("%Y-%m-%d")
            )
            if isinstance(day, str) and len(day) >= 10:
                day = day[:10]
            buckets.setdefault(day, []).append(
                (float(embed or 0), float(retrieve or 0), float(generate or 0))
            )

        data = []
        for day, rows in sorted(buckets.items()):
            n = len(rows)
            data.append(
                {
                    "date": day,
                    "embed_ms": round(sum(r[0] for r in rows) / n, 1),
                    "retrieve_ms": round(sum(r[1] for r in rows) / n, 1),
                    "generate_ms": round(sum(r[2] for r in rows) / n, 1),
                }
            )
        return {"data": data}

    payload, cache_status = await get_or_set_json(key, _compute)
    _set_cache_header(response, cache_status)
    return payload
