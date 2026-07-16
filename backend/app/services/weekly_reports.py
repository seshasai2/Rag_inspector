"""Sync weekly executive report delivery for Celery beat."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.models.models import Pipeline, QueryTrace, User, WeeklyExecutiveReport
from app.services.email_service import send_email_sync
from app.services.trust_scorer import TRUST_SCORE_WINDOW, compute_trust_score_from_metrics


def build_weekly_report_payload(db: Session, user: User, days: int = 7) -> dict:
    pipeline_ids = list(
        db.execute(select(Pipeline.id).where(Pipeline.user_id == user.id)).scalars().all()
    )
    since = datetime.now(timezone.utc) - timedelta(days=days)
    if not pipeline_ids:
        return {
            "total_queries": 0,
            "ai_trust_score": 0,
            "estimated_business_impact": 0,
            "hallucination_count": 0,
            "currency": "INR",
        }

    total, hallucinations = db.execute(
        select(
            func.count(QueryTrace.id),
            func.count(QueryTrace.id).filter(QueryTrace.is_hallucination == True),  # noqa: E712
        ).where(and_(QueryTrace.pipeline_id.in_(pipeline_ids), QueryTrace.traced_at >= since))
    ).one()

    recent_rows = db.execute(
        select(
            QueryTrace.faithfulness_score,
            QueryTrace.grounded_fraction,
            QueryTrace.context_precision_score,
            QueryTrace.is_hallucination,
        )
        .where(and_(QueryTrace.pipeline_id.in_(pipeline_ids), QueryTrace.traced_at >= since))
        .order_by(QueryTrace.traced_at.desc())
        .limit(TRUST_SCORE_WINDOW)
    ).all()

    trust = compute_trust_score_from_metrics(
        faithfulness_scores=[r[0] for r in recent_rows],
        grounded_fractions=[r[1] for r in recent_rows],
        context_precision_scores=[r[2] for r in recent_rows],
        is_hallucination_flags=[r[3] for r in recent_rows],
    )
    return {
        "period_days": days,
        "total_queries": total or 0,
        "ai_trust_score": trust,
        "hallucination_count": hallucinations or 0,
        "estimated_business_impact": int((hallucinations or 0) * 50),
        "currency": "INR",
    }


def render_weekly_report_html(payload: dict) -> str:
    return (
        "<h1>Weekly AI Quality Report</h1>"
        f"<p>AI Trust Score: {payload['ai_trust_score']}/100</p>"
        f"<p>Queries: {payload['total_queries']}</p>"
        f"<p>Hallucinations: {payload['hallucination_count']}</p>"
        f"<p>Estimated impact: {payload['currency']} {payload['estimated_business_impact']}</p>"
    )


def deliver_enabled_weekly_reports(db: Session) -> int:
    """Send email for each enabled weekly report config. Returns count attempted."""
    reports = db.query(WeeklyExecutiveReport).filter(WeeklyExecutiveReport.enabled.is_(True)).all()
    sent = 0
    for report in reports:
        user = db.get(User, report.user_id)
        if not user:
            continue
        payload = build_weekly_report_payload(db, user, days=7)
        html = render_weekly_report_html(payload)
        if send_email_sync(
            report.recipient_email,
            "Weekly RAGInspector Executive Report",
            html,
        ):
            sent += 1
    return sent
