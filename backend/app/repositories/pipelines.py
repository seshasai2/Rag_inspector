"""Thin data-access helpers for duplicated pipeline / trace queries.

Access policy:
- Owners always see their pipelines.
- Accepted org members see pipelines tagged with the same ``organization_id``.
- Mutations that require sole ownership use ``require_pipeline_owner``.
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import OrganizationMember, Pipeline, QueryTrace, User


def _org_pipeline_clause(user: User):
    """SQLAlchemy filter for org-shared pipelines (nullable-safe)."""
    if not user.organization_id:
        return None
    return Pipeline.organization_id == user.organization_id


async def list_pipeline_ids_for_user(db: AsyncSession, user: User) -> list[str]:
    clauses = [Pipeline.user_id == user.id]
    org_clause = _org_pipeline_clause(user)
    if org_clause is not None:
        clauses.append(org_clause)
    result = await db.execute(select(Pipeline.id).where(or_(*clauses)))
    return list(result.scalars().all())


async def list_accessible_pipelines(db: AsyncSession, user: User, *, limit: int):
    clauses = [Pipeline.user_id == user.id]
    org_clause = _org_pipeline_clause(user)
    if org_clause is not None:
        clauses.append(org_clause)
    result = await db.execute(
        select(Pipeline).where(or_(*clauses)).order_by(Pipeline.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def _user_is_accepted_org_member(db: AsyncSession, user: User, organization_id: str) -> bool:
    if not user.organization_id or user.organization_id != organization_id:
        return False
    result = await db.execute(
        select(OrganizationMember.id).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user.id,
            OrganizationMember.accepted_at.isnot(None),
        )
    )
    return result.scalar_one_or_none() is not None


async def user_can_access_pipeline(db: AsyncSession, user: User, pipeline: Pipeline) -> bool:
    if pipeline.user_id == user.id:
        return True
    if pipeline.organization_id and await _user_is_accepted_org_member(
        db, user, pipeline.organization_id
    ):
        return True
    return False


async def get_owned_pipeline(
    db: AsyncSession,
    user: User,
    pipeline_id: str,
) -> Pipeline | None:
    """Return pipeline if the user owns it or has accepted org membership access."""
    result = await db.execute(select(Pipeline).where(Pipeline.id == str(pipeline_id)))
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        return None
    if await user_can_access_pipeline(db, user, pipeline):
        return pipeline
    return None


async def require_owned_pipeline(
    db: AsyncSession,
    user: User,
    pipeline_id: str,
) -> Pipeline:
    """Return an accessible pipeline or raise HTTP 404."""
    pipeline = await get_owned_pipeline(db, user, pipeline_id)
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


async def require_pipeline_owner(
    db: AsyncSession,
    user: User,
    pipeline_id: str,
) -> Pipeline:
    """Owner-only access for destructive / settings mutations."""
    result = await db.execute(
        select(Pipeline).where(Pipeline.id == str(pipeline_id), Pipeline.user_id == user.id)
    )
    pipeline = result.scalar_one_or_none()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


async def get_owned_trace_detail(
    db: AsyncSession,
    user: User,
    trace_id: str,
) -> QueryTrace | None:
    """Load trace + children; access via owner or org-shared pipeline."""
    result = await db.execute(
        select(QueryTrace)
        .options(
            selectinload(QueryTrace.retrieved_chunks),
            selectinload(QueryTrace.grounding_results),
            selectinload(QueryTrace.pipeline),
        )
        .where(QueryTrace.id == trace_id)
    )
    trace = result.scalar_one_or_none()
    if not trace or not trace.pipeline:
        return None
    if not await user_can_access_pipeline(db, user, trace.pipeline):
        return None
    return trace
