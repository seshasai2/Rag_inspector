"""Celery freshness checks (Phase 10.3)."""

from __future__ import annotations

from datetime import datetime, timezone

import structlog

from app.workers.celery_app import celery_app

logger = structlog.get_logger()


@celery_app.task(name="app.workers.freshness_worker.check_document_freshness")
def check_document_freshness(pipeline_id: str | None = None):
    """Recompute freshness for documents; optionally scoped to one pipeline."""
    from sqlalchemy.orm import Session

    from app.db.session import sync_engine
    from app.models.models import Document, KnowledgeGap
    from app.services.document_freshness import refresh_document_freshness

    now = datetime.now(timezone.utc)
    updated = 0
    alerts = 0
    with Session(sync_engine) as db:
        q = db.query(Document)
        if pipeline_id:
            q = q.filter(Document.pipeline_id == pipeline_id)
        docs = q.all()
        for doc in docs:
            prev = doc.freshness_status
            status = refresh_document_freshness(doc, now=now)
            updated += 1
            if status in {"outdated", "needs_review"} and not doc.freshness_alert_sent:
                topic = f"Stale document: {doc.title[:200]}"
                existing = (
                    db.query(KnowledgeGap)
                    .filter(
                        KnowledgeGap.pipeline_id == doc.pipeline_id,
                        KnowledgeGap.topic_label == topic[:500],
                        KnowledgeGap.status == "open",
                    )
                    .first()
                )
                if not existing:
                    db.add(
                        KnowledgeGap(
                            pipeline_id=doc.pipeline_id,
                            topic_label=topic[:500],
                            representative_query=doc.title,
                            query_count=1,
                            priority="high" if status == "needs_review" else "medium",
                            suggested_document_topic=f"Refresh or replace: {doc.title[:200]}",
                            status="open",
                            created_at=now,
                            updated_at=now,
                        )
                    )
                doc.freshness_alert_sent = True
                alerts += 1
            elif status in {"fresh", "aging"} and prev in {"outdated", "needs_review", "stale"}:
                doc.freshness_alert_sent = False
        db.commit()
    logger.info(
        "document_freshness_checked", updated=updated, alerts=alerts, pipeline_id=pipeline_id
    )
    return {"updated": updated, "alerts": alerts}
