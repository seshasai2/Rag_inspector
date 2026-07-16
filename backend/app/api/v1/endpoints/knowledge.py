"""Knowledge gaps API (Phase 10.1)."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.pagination import DEFAULT_PAGE, DEFAULT_PER_PAGE, PageParam, PerPageParam, page_offset
from app.db.session import get_db
from app.models.models import KnowledgeGap, Pipeline, User
from app.schemas.schemas import KnowledgeGapOut, KnowledgeGapStatusUpdate, PaginatedKnowledgeGaps
from app.services.knowledge_gap import normalize_gap_status

router = APIRouter()


@router.get("/gaps", response_model=PaginatedKnowledgeGaps)
async def list_knowledge_gaps(
    pipeline_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: PageParam = DEFAULT_PAGE,
    per_page: PerPageParam = DEFAULT_PER_PAGE,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pipelines_result = await db.execute(
        select(Pipeline.id).where(Pipeline.user_id == current_user.id)
    )
    pipeline_ids = list(pipelines_result.scalars().all())
    if not pipeline_ids:
        return PaginatedKnowledgeGaps(items=[], total=0, page=page, per_page=per_page, pages=0)

    filters = [KnowledgeGap.pipeline_id.in_(pipeline_ids)]
    if pipeline_id:
        filters.append(KnowledgeGap.pipeline_id == str(pipeline_id))
    if status:
        filters.append(KnowledgeGap.status == status.strip().lower())
    if priority:
        filters.append(KnowledgeGap.priority == priority.strip().lower())

    total = (
        await db.execute(select(func.count()).select_from(KnowledgeGap).where(*filters))
    ).scalar_one()
    result = await db.execute(
        select(KnowledgeGap)
        .where(*filters)
        .order_by(KnowledgeGap.query_count.desc(), KnowledgeGap.updated_at.desc())
        .offset(page_offset(page, per_page))
        .limit(per_page)
    )
    items = list(result.scalars().all())
    pages = math.ceil(total / per_page) if per_page else 0
    return PaginatedKnowledgeGaps(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )


@router.patch("/gaps/{gap_id}", response_model=KnowledgeGapOut)
async def update_knowledge_gap_status(
    gap_id: UUID,
    body: KnowledgeGapStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    try:
        status = normalize_gap_status(body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    result = await db.execute(
        select(KnowledgeGap)
        .join(Pipeline, Pipeline.id == KnowledgeGap.pipeline_id)
        .where(KnowledgeGap.id == str(gap_id), Pipeline.user_id == current_user.id)
    )
    gap = result.scalar_one_or_none()
    if not gap:
        raise HTTPException(status_code=404, detail="Knowledge gap not found")

    gap.status = status
    gap.updated_at = datetime.now(timezone.utc)
    if status == "fixed":
        gap.fixed_at = datetime.now(timezone.utc)
    else:
        gap.fixed_at = None
    await db.commit()
    await db.refresh(gap)
    return gap
