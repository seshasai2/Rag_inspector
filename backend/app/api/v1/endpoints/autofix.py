"""Autofix recommendation API (Phase 10.2)."""

from __future__ import annotations

import math
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.pagination import DEFAULT_PAGE, DEFAULT_PER_PAGE, PageParam, PerPageParam, page_offset
from app.db.session import get_db
from app.models.models import FixRecommendation, User
from app.schemas.schemas import (
    FixRecommendationOut,
    PaginatedFixRecommendations,
    TrustVerifyOut,
)
from app.services import autofix as autofix_svc

router = APIRouter()


@router.get("/recommendations", response_model=PaginatedFixRecommendations)
async def list_recommendations(
    pipeline_id: Optional[UUID] = Query(None),
    status: Optional[str] = Query(None),
    page: PageParam = DEFAULT_PAGE,
    per_page: PerPageParam = DEFAULT_PER_PAGE,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    filters = [FixRecommendation.user_id == current_user.id]
    if pipeline_id:
        filters.append(FixRecommendation.pipeline_id == str(pipeline_id))
    if status:
        filters.append(FixRecommendation.status == status.strip().lower())

    total = (
        await db.execute(select(func.count()).select_from(FixRecommendation).where(*filters))
    ).scalar_one()
    result = await db.execute(
        select(FixRecommendation)
        .where(*filters)
        .order_by(FixRecommendation.affected_query_count.desc())
        .offset(page_offset(page, per_page))
        .limit(per_page)
    )
    items = list(result.scalars().all())
    pages = math.ceil(total / per_page) if per_page else 0
    return PaginatedFixRecommendations(
        items=items, total=total, page=page, per_page=per_page, pages=pages
    )


async def _owned_rec(db: AsyncSession, rec_id: UUID, user: User) -> FixRecommendation:
    result = await db.execute(
        select(FixRecommendation).where(
            FixRecommendation.id == str(rec_id),
            FixRecommendation.user_id == user.id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Recommendation not found")
    return rec


@router.post("/recommendations/{rec_id}/apply", response_model=FixRecommendationOut)
async def apply_recommendation(
    rec_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rec = await _owned_rec(db, rec_id, current_user)
    await autofix_svc.apply_recommendation(db, rec)
    await db.commit()
    await db.refresh(rec)
    return rec


@router.post("/recommendations/{rec_id}/dismiss", response_model=FixRecommendationOut)
async def dismiss_recommendation(
    rec_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rec = await _owned_rec(db, rec_id, current_user)
    await autofix_svc.dismiss_recommendation(db, rec)
    await db.commit()
    await db.refresh(rec)
    return rec


@router.post("/recommendations/{rec_id}/verify", response_model=TrustVerifyOut)
async def verify_recommendation(
    rec_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rec = await _owned_rec(db, rec_id, current_user)
    try:
        result = await autofix_svc.verify_recommendation_trust(db, rec)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await db.commit()
    await db.refresh(rec)
    return TrustVerifyOut(
        recommendation_id=rec.id,
        status=rec.status,
        **result,
    )
