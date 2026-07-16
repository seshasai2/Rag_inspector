"""Autofix recommendation actions (Phase 10.2).

Apply/dismiss are workflow states — they do not mutate the customer's KB.
Verify recomputes Trust Score after the user says they shipped a fix.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import FixRecommendation, QueryTrace
from app.services.trust_scorer import TRUST_SCORE_WINDOW, compute_trust_score


async def pipeline_trust_score(db: AsyncSession, pipeline_id: str | None) -> float | None:
    if not pipeline_id:
        return None
    result = await db.execute(
        select(QueryTrace)
        .where(QueryTrace.pipeline_id == pipeline_id)
        .order_by(desc(QueryTrace.traced_at))
        .limit(TRUST_SCORE_WINDOW)
    )
    traces = list(result.scalars().all())
    if not traces:
        return 0.0
    return float(compute_trust_score(traces))


async def apply_recommendation(db: AsyncSession, rec: FixRecommendation) -> FixRecommendation:
    now = datetime.now(timezone.utc)
    if rec.trust_score_before is None:
        rec.trust_score_before = await pipeline_trust_score(db, rec.pipeline_id)
    rec.status = "applied"
    rec.applied_at = now
    rec.dismissed_at = None
    return rec


async def dismiss_recommendation(db: AsyncSession, rec: FixRecommendation) -> FixRecommendation:
    now = datetime.now(timezone.utc)
    rec.status = "dismissed"
    rec.dismissed_at = now
    rec.applied_at = None
    return rec


async def verify_recommendation_trust(db: AsyncSession, rec: FixRecommendation) -> dict[str, Any]:
    """Recompute Trust Score and store as trust_score_after (applied recs only)."""
    if rec.status != "applied":
        raise ValueError("Only applied recommendations can be verified")
    after = await pipeline_trust_score(db, rec.pipeline_id)
    rec.trust_score_after = after
    before = rec.trust_score_before
    delta = None if before is None or after is None else round(after - before, 1)
    return {
        "trust_score_before": before,
        "trust_score_after": after,
        "trust_delta": delta,
        "improved": bool(delta is not None and delta > 0),
    }
