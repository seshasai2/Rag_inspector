import csv
import io
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_min_plan
from app.core.pagination import DEFAULT_LIMIT, LimitParam
from app.core.plan_gate import FEATURE_MIN_PLAN
from app.db.session import get_db
from app.models.models import (
    Pipeline,
    QueryTrace,
    ReportHistory,
    SLAThreshold,
    User,
    WeeklyExecutiveReport,
)
from app.services.audit import record_audit
from app.services.email_service import send_email
from app.services.trust_scorer import TRUST_SCORE_WINDOW, compute_trust_score_from_metrics

router = APIRouter()

_REPORTS_PLAN = FEATURE_MIN_PLAN["executive_reports"]


class WeeklyReportIn(BaseModel):
    recipient_email: EmailStr
    enabled: bool = True


class SLAThresholdIn(BaseModel):
    pipeline_id: str | None = None
    trust_score_min: float = 85.0
    enabled: bool = True


async def owned_pipeline_ids(db: AsyncSession, user: User) -> list[str]:
    result = await db.execute(select(Pipeline.id).where(Pipeline.user_id == user.id))
    return list(result.scalars().all())


async def report_payload(db: AsyncSession, user: User, days: int = 30) -> dict:
    pipeline_ids = await owned_pipeline_ids(db, user)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    if not pipeline_ids:
        return {
            "total_queries": 0,
            "ai_trust_score": 0,
            "estimated_business_impact": 0,
            "knowledge_gaps": [],
            "auto_fix_suggestions": [],
        }

    stats = await db.execute(
        select(
            func.count(QueryTrace.id),
            func.count(QueryTrace.id).filter(QueryTrace.is_hallucination == True),  # noqa: E712
        ).where(and_(QueryTrace.pipeline_id.in_(pipeline_ids), QueryTrace.traced_at >= since))
    )
    total, hallucinations = stats.one()
    estimated_impact = int((hallucinations or 0) * 50)

    recent = await db.execute(
        select(
            QueryTrace.faithfulness_score,
            QueryTrace.grounded_fraction,
            QueryTrace.context_precision_score,
            QueryTrace.is_hallucination,
        )
        .where(and_(QueryTrace.pipeline_id.in_(pipeline_ids), QueryTrace.traced_at >= since))
        .order_by(QueryTrace.traced_at.desc())
        .limit(TRUST_SCORE_WINDOW)
    )
    recent_rows = recent.all()
    trust = compute_trust_score_from_metrics(
        faithfulness_scores=[r[0] for r in recent_rows],
        grounded_fractions=[r[1] for r in recent_rows],
        context_precision_scores=[r[2] for r in recent_rows],
        is_hallucination_flags=[r[3] for r in recent_rows],
    )

    gaps = await db.execute(
        select(QueryTrace.query_text, func.count(QueryTrace.id))
        .where(
            and_(
                QueryTrace.pipeline_id.in_(pipeline_ids),
                QueryTrace.failure_type.in_(["coverage_gap", "retrieval_miss"]),
            )
        )
        .group_by(QueryTrace.query_text)
        .order_by(func.count(QueryTrace.id).desc())
        .limit(10)
    )
    knowledge_gaps = [{"topic": row[0], "count": row[1]} for row in gaps.all()]
    suggestions = [
        f"Create documentation covering {gap['topic'][:120]}." for gap in knowledge_gaps[:5]
    ]
    return {
        "period_days": days,
        "total_queries": total or 0,
        "ai_trust_score": trust,
        "hallucination_count": hallucinations or 0,
        "estimated_business_impact": estimated_impact,
        "currency": "INR",
        "knowledge_gaps": knowledge_gaps,
        "auto_fix_suggestions": suggestions,
    }


@router.get("/executive")
async def executive_report(
    format: str = Query("json", pattern="^(json|csv|pdf)$"),
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(require_min_plan(_REPORTS_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    payload = await report_payload(db, current_user, days)
    history = ReportHistory(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        report_type="executive",
        format=format,
        payload_json=json.dumps(payload),
    )
    db.add(history)
    await record_audit(
        db,
        current_user,
        "report.generated",
        "executive_report",
        None,
        {"format": format, "days": days},
    )
    await db.commit()

    if format == "json":
        return payload
    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["metric", "value"])
        for key, value in payload.items():
            if isinstance(value, (list, dict)):
                value = json.dumps(value)
            writer.writerow([key, value])
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=raginspector_report.csv"},
        )

    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas

    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("RAGInspector Executive Report")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(72, 740, "RAGInspector Executive Report")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(72, 700, f"AI Trust Score: {payload['ai_trust_score']}/100")
    pdf.drawString(
        72, 680, f"Estimated business impact this month: Rs {payload['estimated_business_impact']}"
    )
    pdf.drawString(72, 660, f"Total queries: {payload['total_queries']}")
    pdf.drawString(72, 630, "Auto fix suggestions:")
    y = 610
    for item in payload["auto_fix_suggestions"][:8]:
        pdf.drawString(90, y, f"- {item[:90]}")
        y -= 18
    pdf.save()
    buffer.seek(0)
    return Response(
        content=buffer.getvalue(),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=raginspector_report.pdf"},
    )


@router.get("/history")
async def report_history(
    current_user: User = Depends(require_min_plan(_REPORTS_PLAN)),
    db: AsyncSession = Depends(get_db),
    limit: LimitParam = DEFAULT_LIMIT,
):
    result = await db.execute(
        select(ReportHistory)
        .where(ReportHistory.user_id == current_user.id)
        .order_by(ReportHistory.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/roi")
async def roi_dashboard(
    current_user: User = Depends(require_min_plan(_REPORTS_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    payload = await report_payload(db, current_user, 30)
    return {
        "ai_trust_score": payload["ai_trust_score"],
        "estimated_business_impact_this_month": payload["estimated_business_impact"],
        "risk_reduced": max(0, 100 - payload["hallucination_count"]),
        "currency": payload["currency"],
    }


@router.post("/weekly", status_code=201)
async def configure_weekly_report(
    payload: WeeklyReportIn,
    current_user: User = Depends(require_min_plan(_REPORTS_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    report = WeeklyExecutiveReport(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        recipient_email=payload.recipient_email,
        enabled=payload.enabled,
    )
    db.add(report)
    await record_audit(
        db, current_user, "configuration.changed", "weekly_executive_report", report.id
    )
    await db.commit()
    await db.refresh(report)
    return report


@router.post("/weekly/send-now")
async def send_weekly_now(
    current_user: User = Depends(require_min_plan(_REPORTS_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    payload = await report_payload(db, current_user, 7)
    html = f"<h1>Weekly AI Quality Report</h1><p>AI Trust Score: {payload['ai_trust_score']}/100</p><p>Estimated impact: Rs {payload['estimated_business_impact']}</p>"
    await send_email(current_user.email, "Weekly RAGInspector Executive Report", html)
    await record_audit(db, current_user, "report.sent", "weekly_executive_report", None)
    await db.commit()
    return {"status": "sent", "recipient": current_user.email}


@router.post("/sla", status_code=201)
async def configure_sla(
    payload: SLAThresholdIn,
    current_user: User = Depends(require_min_plan(_REPORTS_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    threshold = SLAThreshold(
        user_id=current_user.id,
        organization_id=current_user.organization_id,
        pipeline_id=payload.pipeline_id,
        trust_score_min=payload.trust_score_min,
        enabled=payload.enabled,
    )
    db.add(threshold)
    await record_audit(
        db,
        current_user,
        "configuration.changed",
        "sla_threshold",
        threshold.id,
        {"trust_score_min": payload.trust_score_min},
    )
    await db.commit()
    await db.refresh(threshold)
    return threshold


@router.get("/sla/status")
async def sla_status(
    current_user: User = Depends(require_min_plan(_REPORTS_PLAN)),
    db: AsyncSession = Depends(get_db),
):
    payload = await report_payload(db, current_user, 7)
    result = await db.execute(
        select(SLAThreshold).where(
            SLAThreshold.user_id == current_user.id, SLAThreshold.enabled == True
        )
    )
    thresholds = result.scalars().all()
    breaches = [
        {
            "threshold_id": t.id,
            "trust_score_min": t.trust_score_min,
            "current_trust_score": payload["ai_trust_score"],
        }
        for t in thresholds
        if payload["ai_trust_score"] < t.trust_score_min
    ]
    return {"status": "breached" if breaches else "healthy", "breaches": breaches}
