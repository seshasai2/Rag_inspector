from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_min_plan
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.db.session import get_db, should_use_sqlite
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


def day_trunc(column):
    if should_use_sqlite():
        return func.strftime("%Y-%m-%d", column)
    return func.date_trunc("day", column)


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

        result = await db.execute(
            select(
                day_trunc(QueryTrace.traced_at).label("day"),
                func.avg(metric_col).label("avg_val"),
                func.count(QueryTrace.id).label("count"),
            )
            .where(and_(*filters))
            .group_by(day_trunc(QueryTrace.traced_at))
            .order_by(day_trunc(QueryTrace.traced_at))
        )

        data = [
            {
                "date": (
                    (row[0] if isinstance(row[0], str) else row[0].strftime("%Y-%m-%d"))
                    if row[0]
                    else None
                ),
                "value": round(float(row[1] or 0), 3),
                "count": row[2],
            }
            for row in result.all()
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

        result = await db.execute(
            select(
                day_trunc(QueryTrace.traced_at).label("day"),
                func.avg(QueryTrace.embed_latency_ms).label("embed"),
                func.avg(QueryTrace.retrieve_latency_ms).label("retrieve"),
                func.avg(QueryTrace.generate_latency_ms).label("generate"),
            )
            .where(and_(*filters))
            .group_by(day_trunc(QueryTrace.traced_at))
            .order_by(day_trunc(QueryTrace.traced_at))
        )

        data = [
            {
                "date": (
                    (row[0] if isinstance(row[0], str) else row[0].strftime("%Y-%m-%d"))
                    if row[0]
                    else None
                ),
                "embed_ms": round(float(row[1] or 0), 1),
                "retrieve_ms": round(float(row[2] or 0), 1),
                "generate_ms": round(float(row[3] or 0), 1),
            }
            for row in result.all()
        ]
        return {"data": data}

    payload, cache_status = await get_or_set_json(key, _compute)
    _set_cache_header(response, cache_status)
    return payload
