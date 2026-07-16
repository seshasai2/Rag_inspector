"""PRD-compatible batch ingest alias for ``POST /api/v1/traces/batch``.

Canonical SDK path remains ``POST /api/v1/ingest/trace`` (single trace).
This endpoint accepts a batch payload and fans out to the same ingest logic.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_scope
from app.core.rate_limit import INGEST_BATCH_LIMIT, limiter
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import TraceIngest
from app.services.ingest_service import ingest_trace as ingest_trace_service

router = APIRouter()


class TraceBatchIn(BaseModel):
    traces: list[TraceIngest] = Field(default_factory=list, max_length=100)


class TraceBatchOut(BaseModel):
    accepted: int
    queued_for_analysis: int
    results: list[dict]


@router.post("/batch", response_model=TraceBatchOut)
@limiter.limit(INGEST_BATCH_LIMIT)
async def ingest_trace_batch(
    request: Request,
    payload: TraceBatchIn,
    user: User = Depends(require_api_scope("ingest:write")),
    db: AsyncSession = Depends(get_db),
):
    if not payload.traces:
        raise HTTPException(status_code=400, detail="traces must be a non-empty list")

    accepted = 0
    queued = 0
    results: list[dict] = []
    for item in payload.traces:
        result = await ingest_trace_service(db, user, item)
        accepted += 1
        if result.status == "accepted":
            queued += 1
        results.append(
            {
                "trace_id": str(result.trace_id),
                "status": result.status,
                "message": result.message,
            }
        )
    return TraceBatchOut(accepted=accepted, queued_for_analysis=queued, results=results)
