"""Benchmark API (Phase 10.6)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.api.deps import require_min_plan
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.db.session import get_db, sync_engine
from app.models.models import User
from app.repositories.pipelines import require_owned_pipeline
from app.services.retrieval_benchmark import run_llm_comparison, run_retrieval_benchmark

router = APIRouter()
_PLAN = FEATURE_MIN_PLAN["benchmark"]


@router.post("/retrieval/{pipeline_id}")
async def retrieval_benchmark(
    pipeline_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(require_min_plan(_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    await require_owned_pipeline(db, current_user, str(pipeline_id))
    with Session(sync_engine) as sync_db:
        return run_retrieval_benchmark(sync_db, str(pipeline_id), limit=limit)


@router.post("/llm/{pipeline_id}")
async def llm_comparison(
    pipeline_id: UUID,
    limit: int = Query(100, ge=1, le=500),
    current_user: User = Depends(require_min_plan(_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    await require_owned_pipeline(db, current_user, str(pipeline_id))
    with Session(sync_engine) as sync_db:
        return run_llm_comparison(sync_db, str(pipeline_id), limit=limit)
