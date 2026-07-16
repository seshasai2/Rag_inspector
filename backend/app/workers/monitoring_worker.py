"""Celery monitoring probes (Phase 10.4)."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog
from sqlalchemy.orm import joinedload

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.workers.monitoring_worker.run_monitoring_probes")
def run_monitoring_probes(pipeline_id: str | None = None):
    """
    Beat task (every minute): evaluate due monitoring configs.

    If ``pipeline_id`` is set, force-run that pipeline's config (run-now).
    """
    from sqlalchemy.orm import Session

    from app.db.session import sync_engine
    from app.models.models import MonitoringConfig, User
    from app.services.monitoring import _parse_json_list, evaluate_pipeline_monitoring
    from app.services.slack_alerts import send_slack_alert_sync

    now = datetime.now(timezone.utc)
    ran = 0
    with Session(sync_engine) as db:
        q = db.query(MonitoringConfig).options(joinedload(MonitoringConfig.pipeline))
        if pipeline_id:
            q = q.filter(MonitoringConfig.pipeline_id == pipeline_id)
        else:
            q = q.filter(
                MonitoringConfig.is_enabled.is_(True),
                (MonitoringConfig.next_run_at.is_(None)) | (MonitoringConfig.next_run_at <= now),
            )
        configs = q.all()
        for config in configs:
            try:
                run = evaluate_pipeline_monitoring(db, config, now=now)
                ran += 1
                alerts = _parse_json_list(run.alerts_triggered)
                if alerts:
                    pipeline = config.pipeline
                    user = (
                        db.query(User).filter(User.id == pipeline.user_id).first()
                        if pipeline
                        else None
                    )
                    if user and user.slack_alert_enabled and user.slack_webhook_url:
                        send_slack_alert_sync(
                            user.slack_webhook_url,
                            (
                                f"Monitoring alert on pipeline `{config.pipeline_id}`: "
                                f"trust={run.trust_score}, hall={run.hallucination_rate}, "
                                f"alerts={len(alerts)}"
                            ),
                            color="danger",
                        )
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.warning(
                    "monitoring_probe_failed",
                    pipeline_id=config.pipeline_id,
                    error=str(exc),
                )
    logger.info("monitoring_probes_done", ran=ran, forced_pipeline=pipeline_id)
    return {"ran": ran}
