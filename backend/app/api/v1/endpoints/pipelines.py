from datetime import datetime, timedelta, timezone
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import Integer, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_min_plan
from app.core.pagination import DEFAULT_LIMIT, LimitParam
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.db.session import get_db
from app.models.models import Pipeline, QueryTrace, User
from app.repositories.pipelines import (
    list_accessible_pipelines,
    require_owned_pipeline,
    require_pipeline_owner,
)
from app.schemas.schemas import PipelineCreate, PipelineOut, PipelineUpdate
from app.services.audit import record_audit
from app.services.hallucination_cost import estimate_hallucination_cost
from app.services.trust_scorer import TRUST_SCORE_WINDOW, compute_trust_score_from_metrics

router = APIRouter()


async def _pipeline_trust_score(db: AsyncSession, pipeline_id: str) -> float:
    recent = await db.execute(
        select(
            QueryTrace.faithfulness_score,
            QueryTrace.grounded_fraction,
            QueryTrace.context_precision_score,
            QueryTrace.is_hallucination,
        )
        .where(QueryTrace.pipeline_id == pipeline_id)
        .order_by(QueryTrace.traced_at.desc())
        .limit(TRUST_SCORE_WINDOW)
    )
    rows = recent.all()
    return compute_trust_score_from_metrics(
        faithfulness_scores=[r[0] for r in rows],
        grounded_fractions=[r[1] for r in rows],
        context_precision_scores=[r[2] for r in rows],
        is_hallucination_flags=[r[3] for r in rows],
    )


@router.get("", response_model=List[PipelineOut])
async def list_pipelines(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    limit: LimitParam = DEFAULT_LIMIT,
):
    return await list_accessible_pipelines(db, current_user, limit=limit)


@router.post("", response_model=PipelineOut, status_code=201)
async def create_pipeline(
    payload: PipelineCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pipeline = Pipeline(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        name=payload.name,
        description=payload.description,
        queries_per_month=(
            payload.queries_per_month if payload.queries_per_month is not None else 10_000
        ),
        cost_per_wrong_answer_usd=(
            payload.cost_per_wrong_answer_usd
            if payload.cost_per_wrong_answer_usd is not None
            else 5.0
        ),
    )
    db.add(pipeline)
    await record_audit(
        db, current_user, "configuration.changed", "pipeline", pipeline.id, {"action": "created"}
    )
    await db.commit()
    await db.refresh(pipeline)
    return pipeline


@router.patch("/{pipeline_id}", response_model=PipelineOut)
async def update_pipeline(
    pipeline_id: UUID,
    payload: PipelineUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pipeline = await require_pipeline_owner(db, current_user, str(pipeline_id))

    data = payload.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(pipeline, key, value)

    await record_audit(
        db,
        current_user,
        "configuration.changed",
        "pipeline",
        pipeline.id,
        {"action": "updated", **data},
    )
    await db.commit()
    await db.refresh(pipeline)
    return pipeline


@router.get("/compare")
async def compare_pipelines(
    a: UUID = Query(...),
    b: UUID = Query(...),
    current_user: User = Depends(require_min_plan(FEATURE_MIN_PLAN["pipeline_compare"])),
    db: AsyncSession = Depends(get_db),
):
    async def get_stats(pid: UUID):
        pipeline = await require_owned_pipeline(db, current_user, str(pid))

        stats_result = await db.execute(
            select(
                func.count(QueryTrace.id),
                func.avg(QueryTrace.faithfulness_score),
                func.avg(QueryTrace.context_precision_score),
                func.avg(QueryTrace.grounded_fraction),
                func.sum(func.cast(QueryTrace.is_hallucination, Integer)),
            ).where(QueryTrace.pipeline_id == str(pid))
        )
        row = stats_result.one()
        total = row[0] or 0
        hall_count = int(row[4] or 0)
        return {
            "pipeline_id": str(pid),
            "name": pipeline.name,
            "total_queries": total,
            "mean_faithfulness": round(row[1] or 0, 3),
            "mean_context_precision": round(row[2] or 0, 3),
            "mean_grounded_fraction": round(row[3] or 0, 3),
            "hallucination_count": hall_count,
            "hallucination_rate": round((hall_count / total) if total > 0 else 0, 3),
            "trust_score": await _pipeline_trust_score(db, str(pid)),
            "hallucination_cost_usd": estimate_hallucination_cost(
                queries_per_month=int(pipeline.queries_per_month or 10_000),
                cost_per_wrong_answer_usd=float(pipeline.cost_per_wrong_answer_usd or 5.0),
                hallucination_rate_value=(hall_count / total) if total > 0 else 0.0,
            ),
            "queries_per_month": int(pipeline.queries_per_month or 10_000),
            "cost_per_wrong_answer_usd": float(pipeline.cost_per_wrong_answer_usd or 5.0),
        }

    return {
        "pipeline_a": await get_stats(a),
        "pipeline_b": await get_stats(b),
    }


@router.get("/{pipeline_id}", response_model=PipelineOut)
async def get_pipeline(
    pipeline_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await require_owned_pipeline(db, current_user, str(pipeline_id))


@router.get("/{pipeline_id}/stats")
async def get_pipeline_stats(
    pipeline_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pipeline = await require_owned_pipeline(db, current_user, str(pipeline_id))

    stats = await db.execute(
        select(
            func.count(QueryTrace.id),
            func.avg(QueryTrace.faithfulness_score),
            func.avg(QueryTrace.context_precision_score),
            func.avg(
                QueryTrace.embed_latency_ms
                + QueryTrace.retrieve_latency_ms
                + QueryTrace.generate_latency_ms
            ),
        ).where(QueryTrace.pipeline_id == str(pipeline_id))
    )
    row = stats.one()
    total = row[0] or 0

    hall_result = await db.execute(
        select(func.count(QueryTrace.id)).where(
            QueryTrace.pipeline_id == str(pipeline_id), QueryTrace.is_hallucination == True
        )
    )
    hall_count = hall_result.scalar() or 0

    last7d = await db.execute(
        select(func.count(QueryTrace.id)).where(
            QueryTrace.pipeline_id == str(pipeline_id),
            QueryTrace.traced_at >= datetime.now(timezone.utc) - timedelta(days=7),
        )
    )
    last7d_count = last7d.scalar() or 0

    return {
        "pipeline_id": str(pipeline_id),
        "name": pipeline.name,
        "total_queries": total,
        "hallucination_rate": round(hall_count / total if total > 0 else 0, 3),
        "mean_faithfulness": round(row[1] or 0, 3),
        "mean_context_precision": round(row[2] or 0, 3),
        "mean_latency_ms": round(row[3] or 0, 1),
        "failure_rate": round(hall_count / total if total > 0 else 0, 3),
        "queries_last_7d": last7d_count,
        "trust_score": await _pipeline_trust_score(db, str(pipeline_id)),
        "hallucination_cost_usd": estimate_hallucination_cost(
            queries_per_month=int(pipeline.queries_per_month or 10_000),
            cost_per_wrong_answer_usd=float(pipeline.cost_per_wrong_answer_usd or 5.0),
            hallucination_rate_value=(hall_count / total) if total > 0 else 0.0,
        ),
        "queries_per_month": int(pipeline.queries_per_month or 10_000),
        "cost_per_wrong_answer_usd": float(pipeline.cost_per_wrong_answer_usd or 5.0),
    }


@router.delete("/{pipeline_id}", status_code=204)
async def delete_pipeline(
    pipeline_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pipeline = await require_pipeline_owner(db, current_user, str(pipeline_id))
    await record_audit(
        db, current_user, "configuration.changed", "pipeline", pipeline.id, {"action": "deleted"}
    )
    await db.delete(pipeline)
    await db.commit()
