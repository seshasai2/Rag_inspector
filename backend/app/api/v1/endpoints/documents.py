"""Documents + freshness API (Phase 10.3)."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.pagination import DEFAULT_PAGE, DEFAULT_PER_PAGE, PageParam, PerPageParam, page_offset
from app.db.session import get_db
from app.models.models import Document, User
from app.repositories.pipelines import list_pipeline_ids_for_user, require_owned_pipeline
from app.schemas.schemas import DocumentCreate, DocumentOut, PaginatedDocuments
from app.services.document_freshness import refresh_document_freshness

router = APIRouter()


@router.get("", response_model=PaginatedDocuments)
async def list_documents(
    pipeline_id: Optional[UUID] = Query(None),
    freshness_status: Optional[str] = Query(None),
    page: PageParam = DEFAULT_PAGE,
    per_page: PerPageParam = DEFAULT_PER_PAGE,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pipeline_ids = await list_pipeline_ids_for_user(db, current_user)
    if not pipeline_ids:
        return PaginatedDocuments(items=[], total=0, page=page, per_page=per_page, pages=0)
    filters = [Document.pipeline_id.in_(pipeline_ids)]
    if pipeline_id:
        filters.append(Document.pipeline_id == str(pipeline_id))
    if freshness_status:
        filters.append(Document.freshness_status == freshness_status.strip().lower())
    total = (
        await db.execute(select(func.count()).select_from(Document).where(*filters))
    ).scalar_one()
    result = await db.execute(
        select(Document)
        .where(*filters)
        .order_by(Document.updated_at.desc())
        .offset(page_offset(page, per_page))
        .limit(per_page)
    )
    items = list(result.scalars().all())
    pages = math.ceil(total / per_page) if per_page else 0
    return PaginatedDocuments(items=items, total=total, page=page, per_page=per_page, pages=pages)


@router.get("/freshness", response_model=PaginatedDocuments)
async def list_freshness(
    pipeline_id: Optional[UUID] = Query(None),
    page: PageParam = DEFAULT_PAGE,
    per_page: PerPageParam = DEFAULT_PER_PAGE,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Documents that are aging or worse (PRD freshness view)."""
    pipeline_ids = await list_pipeline_ids_for_user(db, current_user)
    if not pipeline_ids:
        return PaginatedDocuments(items=[], total=0, page=page, per_page=per_page, pages=0)
    filters = [
        Document.pipeline_id.in_(pipeline_ids),
        Document.freshness_status.in_(("aging", "stale", "outdated", "needs_review")),
    ]
    if pipeline_id:
        filters.append(Document.pipeline_id == str(pipeline_id))
    total = (
        await db.execute(select(func.count()).select_from(Document).where(*filters))
    ).scalar_one()
    result = await db.execute(
        select(Document)
        .where(*filters)
        .order_by(Document.days_since_modified.desc().nullslast())
        .offset(page_offset(page, per_page))
        .limit(per_page)
    )
    items = list(result.scalars().all())
    pages = math.ceil(total / per_page) if per_page else 0
    return PaginatedDocuments(items=items, total=total, page=page, per_page=per_page, pages=pages)


@router.post("", response_model=DocumentOut, status_code=201)
async def create_document(
    body: DocumentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    pipeline = await require_owned_pipeline(db, current_user, str(body.pipeline_id))
    now = datetime.now(timezone.utc)
    doc = Document(
        pipeline_id=pipeline.id,
        title=body.title.strip(),
        source_url=body.source_url,
        document_type=body.document_type,
        last_modified_at=body.last_modified_at or now,
        ingested_at=now,
        chunk_count=body.chunk_count or 0,
        created_at=now,
        updated_at=now,
    )
    refresh_document_freshness(doc, now=now)
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc
