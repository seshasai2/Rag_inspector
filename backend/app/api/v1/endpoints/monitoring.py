"""Monitoring API (Phase 10.4)."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_min_plan
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.db.session import get_db
from app.models.models import MonitoringConfig, MonitoringRun, User
from app.repositories.pipelines import require_owned_pipeline
from app.schemas.schemas import (
    MonitoringConfigOut,
    MonitoringConfigUpdate,
    MonitoringRunNowOut,
    MonitoringRunOut,
)
from app.services.monitoring import dumps_json

router = APIRouter()

_PRO = FEATURE_MIN_PLAN["monitoring"]
_ENTERPRISE = FEATURE_MIN_PLAN["monitoring_run_now"]


def _config_out(cfg: MonitoringConfig) -> MonitoringConfigOut:
    try:
        probes = json.loads(cfg.probe_queries or "[]")
    except json.JSONDecodeError:
        probes = []
    try:
        channels = json.loads(cfg.alert_channels or "[]")
    except json.JSONDecodeError:
        channels = []
    return MonitoringConfigOut(
        id=cfg.id,
        pipeline_id=cfg.pipeline_id,
        is_enabled=cfg.is_enabled,
        interval_minutes=cfg.interval_minutes,
        probe_queries=probes if isinstance(probes, list) else [],
        alert_trust_threshold=cfg.alert_trust_threshold,
        alert_hallucination_threshold=cfg.alert_hallucination_threshold,
        alert_channels=channels if isinstance(channels, list) else [],
        last_run_at=cfg.last_run_at,
        next_run_at=cfg.next_run_at,
        created_at=cfg.created_at,
    )


@router.get("/config/{pipeline_id}", response_model=MonitoringConfigOut)
async def get_monitoring_config(
    pipeline_id: UUID,
    current_user: User = Depends(require_min_plan(_PRO)),
    db: AsyncSession = Depends(get_db),
):
    await require_owned_pipeline(db, current_user, str(pipeline_id))
    result = await db.execute(
        select(MonitoringConfig).where(MonitoringConfig.pipeline_id == str(pipeline_id))
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        # Return defaults without persisting until PUT
        now = datetime.now(timezone.utc)
        return MonitoringConfigOut(
            id="00000000-0000-0000-0000-000000000000",
            pipeline_id=pipeline_id,
            is_enabled=False,
            interval_minutes=60,
            probe_queries=[],
            alert_trust_threshold=70.0,
            alert_hallucination_threshold=0.10,
            alert_channels=[],
            last_run_at=None,
            next_run_at=None,
            created_at=now,
        )
    return _config_out(cfg)


@router.put("/config/{pipeline_id}", response_model=MonitoringConfigOut)
async def upsert_monitoring_config(
    pipeline_id: UUID,
    body: MonitoringConfigUpdate,
    current_user: User = Depends(require_min_plan(_PRO)),
    db: AsyncSession = Depends(get_db),
):
    await require_owned_pipeline(db, current_user, str(pipeline_id))
    result = await db.execute(
        select(MonitoringConfig).where(MonitoringConfig.pipeline_id == str(pipeline_id))
    )
    cfg = result.scalar_one_or_none()
    now = datetime.now(timezone.utc)
    interval = max(1, int(body.interval_minutes or 60))
    if not cfg:
        cfg = MonitoringConfig(
            pipeline_id=str(pipeline_id),
            created_at=now,
            probe_queries="[]",
            alert_channels="[]",
        )
        db.add(cfg)

    cfg.is_enabled = bool(body.is_enabled)
    cfg.interval_minutes = interval
    cfg.probe_queries = dumps_json(body.probe_queries or [])
    cfg.alert_trust_threshold = float(body.alert_trust_threshold)
    cfg.alert_hallucination_threshold = float(body.alert_hallucination_threshold)
    cfg.alert_channels = dumps_json(body.alert_channels or [])
    if cfg.is_enabled and cfg.next_run_at is None:
        cfg.next_run_at = now + timedelta(minutes=interval)
    if not cfg.is_enabled:
        cfg.next_run_at = None
    await db.commit()
    await db.refresh(cfg)
    return _config_out(cfg)


@router.get("/history/{pipeline_id}", response_model=list[MonitoringRunOut])
async def monitoring_history(
    pipeline_id: UUID,
    days: int = Query(7, ge=1, le=90),
    current_user: User = Depends(require_min_plan(_PRO)),
    db: AsyncSession = Depends(get_db),
):
    await require_owned_pipeline(db, current_user, str(pipeline_id))
    since = datetime.now(timezone.utc) - timedelta(days=days)
    result = await db.execute(
        select(MonitoringRun)
        .where(
            MonitoringRun.pipeline_id == str(pipeline_id),
            MonitoringRun.run_at >= since,
        )
        .order_by(MonitoringRun.run_at.desc())
        .limit(200)
    )
    runs = list(result.scalars().all())
    out: list[MonitoringRunOut] = []
    for run in runs:
        try:
            alerts = json.loads(run.alerts_triggered or "[]")
        except json.JSONDecodeError:
            alerts = []
        out.append(
            MonitoringRunOut(
                id=run.id,
                pipeline_id=run.pipeline_id,
                config_id=run.config_id,
                trust_score=run.trust_score,
                hallucination_rate=run.hallucination_rate,
                probes_run=run.probes_run,
                probes_failed=run.probes_failed,
                alerts_triggered=alerts if isinstance(alerts, list) else [],
                regression_detected=run.regression_detected,
                run_at=run.run_at,
            )
        )
    return out


@router.post("/run-now/{pipeline_id}", response_model=MonitoringRunNowOut)
async def run_monitoring_now(
    pipeline_id: UUID,
    current_user: User = Depends(require_min_plan(_ENTERPRISE)),
    db: AsyncSession = Depends(get_db),
):
    await require_owned_pipeline(db, current_user, str(pipeline_id))
    result = await db.execute(
        select(MonitoringConfig).where(MonitoringConfig.pipeline_id == str(pipeline_id))
    )
    cfg = result.scalar_one_or_none()
    if not cfg:
        raise HTTPException(status_code=400, detail="Save a monitoring config before run-now")

    from app.workers.monitoring_worker import run_monitoring_probes

    try:
        async_result = run_monitoring_probes.delay(str(pipeline_id))
        task_id = getattr(async_result, "id", None)
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=f"Celery unavailable: {exc}",
        ) from exc
    return MonitoringRunNowOut(run_id=task_id or str(pipeline_id), pipeline_id=pipeline_id)
