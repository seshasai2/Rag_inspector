"""Regression snapshots + pre-deploy check (Phase 10.5)."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_min_plan
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.db.session import get_db, sync_engine
from app.models.models import RegressionSnapshot, User
from app.repositories.pipelines import require_owned_pipeline
from app.schemas.schemas import (
    PreDeployCheckIn,
    PreDeployCheckOut,
    RegressionCompareIn,
    RegressionCompareOut,
    RegressionSnapshotCreate,
    RegressionSnapshotOut,
)
from app.services import regression as reg

router = APIRouter()

_COMPARE = FEATURE_MIN_PLAN["regression_compare"]
_PRE_DEPLOY = FEATURE_MIN_PLAN["regression_pre_deploy"]


def _out(snap: RegressionSnapshot) -> RegressionSnapshotOut:
    return RegressionSnapshotOut(
        id=snap.id,
        pipeline_id=snap.pipeline_id,
        snapshot_label=snap.snapshot_label,
        trust_score=snap.trust_score,
        faithfulness_avg=snap.faithfulness_avg,
        context_precision_avg=snap.context_precision_avg,
        hallucination_rate=snap.hallucination_rate,
        trace_count=snap.trace_count,
        snapshot_at=snap.snapshot_at,
    )


@router.get("/snapshots/{pipeline_id}", response_model=list[RegressionSnapshotOut])
async def list_snapshots(
    pipeline_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await require_owned_pipeline(db, current_user, str(pipeline_id))
    result = await db.execute(
        select(RegressionSnapshot)
        .where(RegressionSnapshot.pipeline_id == str(pipeline_id))
        .order_by(RegressionSnapshot.snapshot_at.desc())
        .limit(100)
    )
    return [_out(s) for s in result.scalars().all()]


@router.post("/snapshots/{pipeline_id}", response_model=RegressionSnapshotOut, status_code=201)
async def create_snapshot(
    pipeline_id: UUID,
    body: RegressionSnapshotCreate,
    current_user: User = Depends(require_min_plan(_COMPARE)),
    db: AsyncSession = Depends(get_db),
):
    await require_owned_pipeline(db, current_user, str(pipeline_id))
    with Session(sync_engine) as sync_db:
        snap = reg.create_snapshot(
            sync_db,
            str(pipeline_id),
            snapshot_label=body.snapshot_label,
        )
        sync_db.commit()
        sync_db.refresh(snap)
        return _out(snap)


@router.post("/compare", response_model=RegressionCompareOut)
async def compare_snapshots(
    body: RegressionCompareIn,
    current_user: User = Depends(require_min_plan(_COMPARE)),
    db: AsyncSession = Depends(get_db),
):
    await require_owned_pipeline(db, current_user, str(body.pipeline_id))
    baseline_result = await db.execute(
        select(RegressionSnapshot).where(
            RegressionSnapshot.id == str(body.baseline_snapshot_id),
            RegressionSnapshot.pipeline_id == str(body.pipeline_id),
        )
    )
    baseline = baseline_result.scalar_one_or_none()
    if not baseline:
        raise HTTPException(status_code=404, detail="Baseline snapshot not found")

    if body.compare_to == "current":
        with Session(sync_engine) as sync_db:
            traces = reg.load_recent_traces(sync_db, str(body.pipeline_id))
            current_metrics = reg.metrics_from_traces(traces)
            current_metrics["id"] = None
            current_metrics["pipeline_id"] = str(body.pipeline_id)
            current_metrics["snapshot_label"] = "current"
            current_metrics["snapshot_at"] = datetime.now(timezone.utc)
        current_out = RegressionSnapshotOut(
            id="00000000-0000-0000-0000-000000000000",
            pipeline_id=body.pipeline_id,
            snapshot_label="current",
            trust_score=current_metrics["trust_score"],
            faithfulness_avg=current_metrics.get("faithfulness_avg"),
            context_precision_avg=current_metrics.get("context_precision_avg"),
            hallucination_rate=current_metrics.get("hallucination_rate"),
            trace_count=current_metrics["trace_count"],
            snapshot_at=current_metrics["snapshot_at"],
        )
        current_dict = current_metrics
    else:
        if not body.compare_to:
            raise HTTPException(status_code=400, detail="compare_to required")
        other = await db.execute(
            select(RegressionSnapshot).where(
                RegressionSnapshot.id == str(body.compare_to),
                RegressionSnapshot.pipeline_id == str(body.pipeline_id),
            )
        )
        current_snap = other.scalar_one_or_none()
        if not current_snap:
            raise HTTPException(status_code=404, detail="Compare snapshot not found")
        current_out = _out(current_snap)
        current_dict = reg.snapshot_to_dict(current_snap)

    delta = reg.compare_metrics(reg.snapshot_to_dict(baseline), current_dict)
    return RegressionCompareOut(
        baseline=_out(baseline),
        current=current_out,
        delta=delta,
    )


@router.post("/pre-deploy-check", response_model=PreDeployCheckOut)
async def pre_deploy_check(
    body: PreDeployCheckIn,
    response: Response,
    current_user: User = Depends(require_min_plan(_PRE_DEPLOY)),
    db: AsyncSession = Depends(get_db),
):
    await require_owned_pipeline(db, current_user, str(body.pipeline_id))

    with Session(sync_engine) as sync_db:
        baseline = (
            sync_db.query(RegressionSnapshot)
            .filter(RegressionSnapshot.pipeline_id == str(body.pipeline_id))
            .order_by(RegressionSnapshot.snapshot_at.desc())
            .first()
        )
        if not baseline:
            # First deploy: capture baseline and pass
            snap = reg.create_snapshot(
                sync_db,
                str(body.pipeline_id),
                snapshot_label=body.deploy_label or "baseline",
            )
            sync_db.commit()
            sync_db.refresh(snap)
            result = {
                "passed": True,
                "trust_score": snap.trust_score,
                "baseline_trust_score": snap.trust_score,
                "regression_risk": "low",
                "blocking_issues": [],
                "regression_severity": "none",
                "snapshot_id": str(snap.id),
            }
            response.status_code = 200
            return PreDeployCheckOut(**result)

        traces = reg.load_recent_traces(sync_db, str(body.pipeline_id))
        current = reg.metrics_from_traces(traces)
        result = reg.pre_deploy_result(reg.snapshot_to_dict(baseline), current)

        # Persist post-check snapshot labeled with deploy
        snap = reg.create_snapshot(
            sync_db,
            str(body.pipeline_id),
            snapshot_label=body.deploy_label
            or f"pre-deploy-{datetime.now(timezone.utc).isoformat()}",
        )
        sync_db.commit()
        result["snapshot_id"] = str(snap.id)

    response.status_code = 200 if result["passed"] else 422
    return PreDeployCheckOut(**{k: v for k, v in result.items() if k != "delta"})
