import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.pagination import DEFAULT_PAGE, DEFAULT_PER_PAGE, PageParam, PerPageParam, page_offset
from app.db.session import get_db
from app.models.models import ChunkStat, Pipeline, User
from app.schemas.schemas import PaginatedChunks

router = APIRouter()


@router.get("", response_model=PaginatedChunks)
async def list_chunks(
    pipeline_id: Optional[UUID] = Query(None),
    flagged_only: bool = Query(False),
    sort_by: str = Query("retrieval_count"),
    sort_order: str = Query("desc"),
    search: Optional[str] = Query(None),
    page: PageParam = DEFAULT_PAGE,
    per_page: PerPageParam = DEFAULT_PER_PAGE,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Get user's pipeline IDs
    pipelines_result = await db.execute(
        select(Pipeline.id).where(Pipeline.user_id == current_user.id)
    )
    pipeline_ids = [r for r in pipelines_result.scalars().all()]

    if not pipeline_ids:
        return PaginatedChunks(items=[], total=0, page=page, per_page=per_page, pages=0)

    filters = [ChunkStat.pipeline_id.in_(pipeline_ids)]
    if pipeline_id:
        filters.append(ChunkStat.pipeline_id == pipeline_id)
    if flagged_only:
        filters.append(ChunkStat.is_flagged == True)
    if search:
        filters.append(ChunkStat.text.ilike(f"%{search}%"))

    count_result = await db.execute(select(func.count(ChunkStat.id)).where(and_(*filters)))
    total = count_result.scalar() or 0

    sort_col = getattr(ChunkStat, sort_by, ChunkStat.retrieval_count)
    order = sort_col.desc() if sort_order == "desc" else sort_col.asc()

    result = await db.execute(
        select(ChunkStat)
        .where(and_(*filters))
        .order_by(order)
        .offset(page_offset(page, per_page))
        .limit(per_page)
    )
    chunks = result.scalars().all()

    return PaginatedChunks(
        items=chunks,
        total=total,
        page=page,
        per_page=per_page,
        pages=math.ceil(total / per_page) if total > 0 else 0,
    )


@router.get("/summary")
async def chunks_quality_summary(
    pipeline_id: Optional[UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregate chunk quality stats for heatmap header."""
    from app.services.chunk_quality import (
        LOW_QUALITY_MAX_CITATION_RATE,
        LOW_QUALITY_MIN_RETRIEVALS,
    )

    pipelines_result = await db.execute(
        select(Pipeline.id).where(Pipeline.user_id == current_user.id)
    )
    pipeline_ids = list(pipelines_result.scalars().all())
    if not pipeline_ids:
        return {
            "total_chunks": 0,
            "flagged_count": 0,
            "low_quality_eligible": 0,
            "avg_citation_rate": 0.0,
            "auto_flag_rule": {
                "min_retrievals": LOW_QUALITY_MIN_RETRIEVALS,
                "max_citation_rate": LOW_QUALITY_MAX_CITATION_RATE,
            },
        }

    filters = [ChunkStat.pipeline_id.in_(pipeline_ids)]
    if pipeline_id:
        filters.append(ChunkStat.pipeline_id == pipeline_id)

    total = (await db.execute(select(func.count(ChunkStat.id)).where(and_(*filters)))).scalar() or 0
    flagged = (
        await db.execute(
            select(func.count(ChunkStat.id)).where(
                and_(*filters, ChunkStat.is_flagged == True)  # noqa: E712
            )
        )
    ).scalar() or 0
    eligible = (
        await db.execute(
            select(func.count(ChunkStat.id)).where(
                and_(
                    *filters,
                    ChunkStat.retrieval_count >= LOW_QUALITY_MIN_RETRIEVALS,
                    ChunkStat.citation_rate < LOW_QUALITY_MAX_CITATION_RATE,
                )
            )
        )
    ).scalar() or 0
    avg_rate = (
        await db.execute(select(func.avg(ChunkStat.citation_rate)).where(and_(*filters)))
    ).scalar() or 0

    return {
        "total_chunks": total,
        "flagged_count": flagged,
        "low_quality_eligible": eligible,
        "avg_citation_rate": round(float(avg_rate), 3),
        "auto_flag_rule": {
            "min_retrievals": LOW_QUALITY_MIN_RETRIEVALS,
            "max_citation_rate": LOW_QUALITY_MAX_CITATION_RATE,
        },
    }


@router.post("/{chunk_id}/flag")
async def flag_chunk(
    chunk_id: str,
    pipeline_id: UUID = Query(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify pipeline ownership
    p_result = await db.execute(
        select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.user_id == current_user.id)
    )
    if not p_result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized")

    result = await db.execute(
        select(ChunkStat).where(
            ChunkStat.chunk_id == chunk_id,
            ChunkStat.pipeline_id == pipeline_id,
        )
    )
    chunk = result.scalar_one_or_none()
    if not chunk:
        raise HTTPException(status_code=404, detail="Chunk not found")

    chunk.is_flagged = not chunk.is_flagged
    await db.commit()
    return {"chunk_id": chunk_id, "is_flagged": chunk.is_flagged}
