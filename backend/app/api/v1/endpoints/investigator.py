"""AI Investigator API (Phase 10.8)."""

from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_min_plan
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.db.session import get_db
from app.models.models import Pipeline, User
from app.services.ai_investigator import investigate
from app.services.dashboard_metrics import build_dashboard_metrics

router = APIRouter()
_PLAN = FEATURE_MIN_PLAN["investigator"]


class InvestigateIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    pipeline_id: Optional[UUID] = None


@router.post("/ask")
async def ask_investigator(
    body: InvestigateIn,
    current_user: User = Depends(require_min_plan(_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    pipeline_id = str(body.pipeline_id) if body.pipeline_id else None
    if pipeline_id:
        result = await db.execute(
            select(Pipeline).where(Pipeline.id == pipeline_id, Pipeline.user_id == current_user.id)
        )
        if not result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Pipeline not found")
    metrics = await build_dashboard_metrics(db, current_user, pipeline_id=pipeline_id)
    # Convert pydantic/dataclass-like to dict
    if hasattr(metrics, "model_dump"):
        payload = metrics.model_dump()
    elif hasattr(metrics, "dict"):
        payload = metrics.dict()
    elif isinstance(metrics, dict):
        payload = metrics
    else:
        payload = dict(metrics.__dict__) if hasattr(metrics, "__dict__") else {}
    return await investigate(body.question, payload)
