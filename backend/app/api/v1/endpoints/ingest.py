from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_api_scope
from app.core.rate_limit import INGEST_TRACE_LIMIT, limiter
from app.db.session import get_db
from app.models.models import User
from app.schemas.schemas import TraceIngest, TraceIngestResponse
from app.services.ingest_service import PLAN_LIMITS
from app.services.ingest_service import ingest_trace as ingest_trace_service

# Re-exported for billing usage endpoint + subscription plan tests.
__all__ = ["router", "PLAN_LIMITS", "ingest_trace"]

router = APIRouter()


@router.post("/trace", response_model=TraceIngestResponse, status_code=202)
@limiter.limit(INGEST_TRACE_LIMIT)
async def ingest_trace(
    request: Request,
    payload: TraceIngest,
    user: User = Depends(require_api_scope("ingest:write")),
    db: AsyncSession = Depends(get_db),
):
    return await ingest_trace_service(db, user, payload)
