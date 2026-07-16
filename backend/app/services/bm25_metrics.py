"""Aggregate BM25 vs vector comparison metrics."""

from __future__ import annotations

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import Pipeline, QueryTrace, RetrievedChunk, User
from app.services.bm25_service import BM25_BETTER_MARGIN, aggregate_bm25_outperform_rate


async def build_bm25_aggregate(
    db: AsyncSession,
    current_user: User,
    pipeline_id: str | None = None,
    pipeline_ids: list[str] | None = None,
) -> dict:
    """
    Compute PRD F4 aggregate: share of traces where top BM25 > top vector + margin.
    """
    if pipeline_ids is None:
        pipelines_result = await db.execute(
            select(Pipeline.id).where(Pipeline.user_id == current_user.id)
        )
        pipeline_ids = list(pipelines_result.scalars().all())
    empty = aggregate_bm25_outperform_rate([])
    empty["pipeline_id"] = pipeline_id
    if not pipeline_ids:
        return empty

    filters = [QueryTrace.pipeline_id.in_(pipeline_ids)]
    if pipeline_id:
        filters.append(QueryTrace.pipeline_id == pipeline_id)

    # Per-trace max BM25 and max vector score among retrieved chunks
    per_trace = (
        select(
            RetrievedChunk.trace_id.label("trace_id"),
            func.max(RetrievedChunk.bm25_score).label("bm25_max"),
            func.max(RetrievedChunk.similarity_score).label("vector_max"),
        )
        .join(QueryTrace, QueryTrace.id == RetrievedChunk.trace_id)
        .where(and_(*filters))
        .group_by(RetrievedChunk.trace_id)
    )
    rows = (await db.execute(per_trace)).all()

    flags: list[bool | None] = []
    for row in rows:
        bm25_max = row.bm25_max
        vector_max = row.vector_max
        if bm25_max is None or vector_max is None:
            flags.append(None)
            continue
        flags.append(float(bm25_max) > float(vector_max) + BM25_BETTER_MARGIN)

    result = aggregate_bm25_outperform_rate(flags)
    result["pipeline_id"] = pipeline_id
    result["margin"] = BM25_BETTER_MARGIN
    return result
