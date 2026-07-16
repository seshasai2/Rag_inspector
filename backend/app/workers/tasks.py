"""
Celery tasks for async RAG analysis.
"""

from datetime import datetime, timezone

import structlog
from celery import Task

from app.core.config import settings as app_settings
from app.workers.celery_app import celery_app

logger = structlog.get_logger()


class DatabaseTask(Task):
    """Base task that manages sync DB connections for Celery."""

    _session = None

    def get_sync_session(self):
        from sqlalchemy.orm import Session

        from app.db.session import sync_engine

        return Session(sync_engine)


@celery_app.task(
    bind=True,
    base=DatabaseTask,
    max_retries=3,
    default_retry_delay=30,
    soft_time_limit=app_settings.ANALYSIS_SOFT_TIME_LIMIT_SECONDS,
    time_limit=app_settings.ANALYSIS_HARD_TIME_LIMIT_SECONDS,
    name="app.workers.tasks.run_analysis",
)
def run_analysis(self, trace_id: str):
    """Thin Celery wrapper around the sync analysis pipeline."""
    from celery.exceptions import SoftTimeLimitExceeded
    from sqlalchemy.orm import Session

    from app.db.session import sync_engine
    from app.services.analysis_pipeline import _mark_failed, analyze_trace

    with Session(sync_engine) as db:
        try:
            return analyze_trace(db, trace_id)
        except SoftTimeLimitExceeded as exc:
            _mark_failed(db, trace_id, exc)
            raise
        except Exception as exc:
            # analyze_trace already marks failed when it raises; retry transient errors.
            raise self.retry(exc=exc)


@celery_app.task(name="app.workers.tasks.reset_monthly_traces")
def reset_monthly_traces():
    """Reset monthly trace counters for all users."""
    from sqlalchemy.orm import Session

    from app.db.session import sync_engine
    from app.models.models import User

    with Session(sync_engine) as db:
        users = db.query(User).all()
        for user in users:
            user.traces_this_month = 0
            user.traces_reset_at = datetime.now(timezone.utc)
        db.commit()
        logger.info("Monthly traces reset", user_count=len(users))


@celery_app.task(name="app.workers.tasks.update_chunk_citation_rates")
def update_chunk_citation_rates():
    """Recalculate citation rates and flag low-quality chunks (PRD F5)."""
    from sqlalchemy.orm import Session

    from app.db.session import sync_engine
    from app.models.models import ChunkStat
    from app.services.chunk_quality import apply_chunk_quality_update

    with Session(sync_engine) as db:
        chunks = db.query(ChunkStat).all()
        flagged = 0
        for chunk in chunks:
            updated = apply_chunk_quality_update(
                retrieval_count=chunk.retrieval_count,
                citation_count=chunk.citation_count,
                currently_flagged=bool(chunk.is_flagged),
                auto_unflag=True,
            )
            chunk.citation_rate = updated["citation_rate"]
            chunk.is_flagged = updated["is_flagged"]
            if updated["newly_auto_flagged"]:
                flagged += 1
        db.commit()
        logger.info("Citation rates updated", flagged_new=flagged)


@celery_app.task(
    bind=True, max_retries=3, default_retry_delay=60, name="app.workers.tasks.deliver_webhook"
)
def deliver_webhook(self, delivery_id: str):
    import json
    from datetime import datetime

    import httpx
    from sqlalchemy.orm import Session

    from app.db.session import sync_engine
    from app.models.models import IntegrationWebhook, WebhookDelivery

    with Session(sync_engine) as db:
        delivery = db.query(WebhookDelivery).filter(WebhookDelivery.id == delivery_id).first()
        if not delivery:
            return
        webhook = (
            db.query(IntegrationWebhook)
            .filter(IntegrationWebhook.id == delivery.webhook_id)
            .first()
        )
        if not webhook or not webhook.is_active:
            delivery.status = "skipped"
            db.commit()
            return
        try:
            import hashlib
            import hmac

            from app.core.security import decrypt_secret

            delivery.attempts += 1
            payload = json.loads(delivery.payload_json)
            body = json.dumps(payload, separators=(",", ":"), sort_keys=True)
            headers = {
                "X-RAGInspector-Event": delivery.event_type,
                "Content-Type": "application/json",
            }
            stored = webhook.signing_secret_hash or ""
            if stored.startswith("enc:v1:"):
                try:
                    secret = decrypt_secret(stored)
                    signature = hmac.new(
                        secret.encode("utf-8"), body.encode("utf-8"), hashlib.sha256
                    ).hexdigest()
                    headers["X-RAGInspector-Signature"] = f"sha256={signature}"
                except Exception:
                    pass
            with httpx.Client(timeout=10.0) as client:
                response = client.post(
                    webhook.webhook_url,
                    content=body,
                    headers=headers,
                )
            if response.status_code >= 400:
                raise RuntimeError(f"HTTP {response.status_code}")
            delivery.status = "delivered"
            delivery.delivered_at = datetime.now(timezone.utc)
            delivery.last_error = None
            db.commit()
        except Exception as exc:
            delivery.status = "failed"
            delivery.last_error = str(exc)
            db.commit()
            raise self.retry(exc=exc)


@celery_app.task(name="app.workers.tasks.send_weekly_executive_reports")
def send_weekly_executive_reports():
    from sqlalchemy.orm import Session

    from app.db.session import sync_engine
    from app.services.weekly_reports import deliver_enabled_weekly_reports

    with Session(sync_engine) as db:
        sent = deliver_enabled_weekly_reports(db)
        logger.info("Weekly executive reports delivered", count=sent)
