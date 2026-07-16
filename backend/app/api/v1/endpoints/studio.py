"""Studio API (Phase 10.7)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_min_plan
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.db.session import get_db
from app.models.models import ChunkStat, QueryTrace, RetrievedChunk, User
from app.repositories.pipelines import require_owned_pipeline
from app.services import studio as studio_svc

router = APIRouter()
_PLAN = FEATURE_MIN_PLAN["studio"]


class PromptAnalyzeIn(BaseModel):
    prompt_text: str


class SimulateIn(BaseModel):
    pipeline_id: UUID
    trace_id: UUID
    top_k: int = 3


@router.post("/prompt/analyze")
async def prompt_analyze(
    body: PromptAnalyzeIn,
    _: User = Depends(require_min_plan(_PLAN)),
):
    return studio_svc.analyze_prompt(body.prompt_text)


@router.get("/chunks/optimize/{pipeline_id}")
async def chunk_optimize(
    pipeline_id: UUID,
    current_user: User = Depends(require_min_plan(_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    await require_owned_pipeline(db, current_user, str(pipeline_id))
    result = await db.execute(
        select(ChunkStat).where(ChunkStat.pipeline_id == str(pipeline_id)).limit(500)
    )
    rows = [
        {
            "chunk_id": c.chunk_id,
            "retrieval_count": c.retrieval_count,
            "citation_count": c.citation_count,
            "citation_rate": c.citation_rate,
        }
        for c in result.scalars().all()
    ]
    return studio_svc.chunk_optimizer_suggestions(rows)


@router.post("/simulate")
async def simulate_retrieval(
    body: SimulateIn,
    current_user: User = Depends(require_min_plan(_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    await require_owned_pipeline(db, current_user, str(body.pipeline_id))
    trace_result = await db.execute(
        select(QueryTrace).where(
            QueryTrace.id == str(body.trace_id),
            QueryTrace.pipeline_id == str(body.pipeline_id),
        )
    )
    if not trace_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Trace not found")
    chunks_result = await db.execute(
        select(RetrievedChunk).where(RetrievedChunk.trace_id == str(body.trace_id))
    )
    chunks = [
        {
            "chunk_id": c.chunk_id,
            "similarity_score": c.similarity_score,
            "was_cited": c.was_cited,
        }
        for c in chunks_result.scalars().all()
    ]
    return studio_svc.simulate_top_k(chunks, top_k=body.top_k)
