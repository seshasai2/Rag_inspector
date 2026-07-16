"""Dashboard metrics aggregation — keep HTTP handlers thin."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import Integer, and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.models import FixRecommendation, Pipeline, QueryTrace, User
from app.schemas.schemas import DashboardMetrics
from app.services.hallucination_cost import (
    DEFAULT_COST_PER_WRONG_ANSWER_USD,
    DEFAULT_QUERIES_PER_MONTH,
    estimate_hallucination_cost,
)
from app.services.metric_trends import percent_change
from app.services.trust_scorer import TRUST_SCORE_WINDOW, compute_trust_score_from_metrics


async def hallucination_rates_by_pipeline(
    db: AsyncSession,
    pipeline_ids: list[str],
) -> dict[str, float]:
    """One grouped query — avoids per-pipeline N+1 for Hallucination Cost."""
    if not pipeline_ids:
        return {}
    result = await db.execute(
        select(
            QueryTrace.pipeline_id,
            func.count(QueryTrace.id),
            func.coalesce(
                func.sum(func.cast(QueryTrace.is_hallucination, Integer)),
                0,
            ),
        )
        .where(QueryTrace.pipeline_id.in_(pipeline_ids))
        .group_by(QueryTrace.pipeline_id)
    )
    rates: dict[str, float] = {}
    for pid, total, hall in result.all():
        total_i = int(total or 0)
        hall_i = int(hall or 0)
        rates[str(pid)] = (hall_i / total_i) if total_i > 0 else 0.0
    return rates


async def build_dashboard_metrics(
    db: AsyncSession,
    current_user: User,
    pipeline_id: str | None = None,
) -> DashboardMetrics:
    pipelines_result = await db.execute(select(Pipeline).where(Pipeline.user_id == current_user.id))
    owned_pipelines = list(pipelines_result.scalars().all())
    pipeline_ids = [p.id for p in owned_pipelines]
    pipeline_map = {str(p.id): p.name for p in owned_pipelines}

    empty = DashboardMetrics(
        total_queries=0,
        hallucination_rate=0.0,
        mean_faithfulness=0.0,
        mean_context_precision=0.0,
        trustworthiness_score=0.0,
        queries_today=0,
        queries_this_week=0,
        failure_type_counts={},
        recent_failures=[],
        recent_recommendations=[],
        queries_trend_pct=None,
        hallucination_rate_trend_pct=None,
        faithfulness_trend_pct=None,
        hallucination_cost_usd=0.0,
        queries_per_month=DEFAULT_QUERIES_PER_MONTH,
        cost_per_wrong_answer_usd=DEFAULT_COST_PER_WRONG_ANSWER_USD,
        cost_pipeline_id=None,
        bm25_outperform_rate=None,
        bm25_traces_compared=0,
        bm25_summary=None,
    )
    if not pipeline_ids:
        return empty

    filters = [QueryTrace.pipeline_id.in_(pipeline_ids)]
    if pipeline_id:
        filters.append(QueryTrace.pipeline_id == pipeline_id)

    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    # Single aggregate pass for headline counts / means
    stats = await db.execute(
        select(
            func.count(QueryTrace.id),
            func.avg(QueryTrace.faithfulness_score),
            func.avg(QueryTrace.context_precision_score),
            func.coalesce(func.sum(func.cast(QueryTrace.is_hallucination, Integer)), 0),
            func.coalesce(
                func.sum(case((QueryTrace.traced_at >= today, 1), else_=0)),
                0,
            ),
            func.coalesce(
                func.sum(case((QueryTrace.traced_at >= week_ago, 1), else_=0)),
                0,
            ),
        ).where(and_(*filters))
    )
    row = stats.one()
    total = int(row[0] or 0)
    hall_count = int(row[3] or 0)
    today_count = int(row[4] or 0)
    week_count = int(row[5] or 0)

    # Hero Trust Score: documented 30/30/20/20 formula over recent window
    recent_metrics = await db.execute(
        select(
            QueryTrace.faithfulness_score,
            QueryTrace.grounded_fraction,
            QueryTrace.context_precision_score,
            QueryTrace.is_hallucination,
        )
        .where(and_(*filters))
        .order_by(QueryTrace.traced_at.desc())
        .limit(TRUST_SCORE_WINDOW)
    )
    recent_rows = recent_metrics.all()
    trustworthiness_score = compute_trust_score_from_metrics(
        faithfulness_scores=[r[0] for r in recent_rows],
        grounded_fractions=[r[1] for r in recent_rows],
        context_precision_scores=[r[2] for r in recent_rows],
        is_hallucination_flags=[r[3] for r in recent_rows],
    )

    now = datetime.now(timezone.utc)
    current_start = now - timedelta(days=7)
    previous_start = now - timedelta(days=14)

    async def _window_stats(start: datetime, end: datetime) -> tuple[int, int, float]:
        window_filters = and_(*filters, QueryTrace.traced_at >= start, QueryTrace.traced_at < end)
        wrow = (
            await db.execute(
                select(
                    func.count(QueryTrace.id),
                    func.coalesce(
                        func.sum(func.cast(QueryTrace.is_hallucination, Integer)),
                        0,
                    ),
                    func.avg(QueryTrace.faithfulness_score),
                ).where(window_filters)
            )
        ).one()
        return int(wrow[0] or 0), int(wrow[1] or 0), float(wrow[2] or 0)

    curr_count, curr_hall, curr_faith = await _window_stats(current_start, now)
    prev_count, prev_hall, prev_faith = await _window_stats(previous_start, current_start)
    curr_hall_rate = (curr_hall / curr_count) if curr_count > 0 else 0.0
    prev_hall_rate = (prev_hall / prev_count) if prev_count > 0 else 0.0

    fail_result = await db.execute(
        select(QueryTrace.failure_type, func.count(QueryTrace.id))
        .where(and_(*filters, QueryTrace.failure_type != None))  # noqa: E711
        .group_by(QueryTrace.failure_type)
    )
    failure_counts = {
        (r[0].value if hasattr(r[0], "value") else str(r[0])): r[1] for r in fail_result.all()
    }

    fail_traces = await db.execute(
        select(QueryTrace)
        .where(and_(*filters, QueryTrace.is_hallucination == True))  # noqa: E712
        .order_by(QueryTrace.traced_at.desc())
        .limit(5)
    )

    recent_failures = [
        {
            "id": str(t.id),
            "pipeline_id": str(t.pipeline_id),
            "pipeline_name": pipeline_map.get(str(t.pipeline_id)),
            "query_text": t.query_text,
            "faithfulness_score": t.faithfulness_score,
            "failure_type": t.failure_type.value if t.failure_type else None,
            "traced_at": t.traced_at.isoformat() if t.traced_at else None,
            "analysis_status": t.analysis_status,
        }
        for t in fail_traces.scalars().all()
    ]

    recs_result = await db.execute(
        select(FixRecommendation)
        .where(
            FixRecommendation.user_id == current_user.id,
            FixRecommendation.status == "open",
        )
        .order_by(FixRecommendation.affected_query_count.desc())
        .limit(5)
    )
    recent_recommendations = [
        {
            "id": str(r.id),
            "recommendation_type": r.recommendation_type,
            "topic_description": r.topic_description,
            "affected_query_count": r.affected_query_count,
        }
        for r in recs_result.scalars().all()
    ]

    # Hallucination Cost: per selected pipeline, or sum across owned pipelines (no N+1)
    cost_pipeline_id: str | None = None
    queries_per_month = DEFAULT_QUERIES_PER_MONTH
    cost_per_wrong = DEFAULT_COST_PER_WRONG_ANSWER_USD
    hallucination_cost_usd = 0.0

    if pipeline_id:
        selected = next((p for p in owned_pipelines if str(p.id) == str(pipeline_id)), None)
        if selected:
            cost_pipeline_id = str(selected.id)
            queries_per_month = int(selected.queries_per_month or DEFAULT_QUERIES_PER_MONTH)
            cost_per_wrong = float(
                selected.cost_per_wrong_answer_usd
                if selected.cost_per_wrong_answer_usd is not None
                else DEFAULT_COST_PER_WRONG_ANSWER_USD
            )
            rate = (hall_count / total) if total > 0 else 0.0
            hallucination_cost_usd = estimate_hallucination_cost(
                queries_per_month=queries_per_month,
                cost_per_wrong_answer_usd=cost_per_wrong,
                hallucination_rate_value=rate,
            )
    elif owned_pipelines:
        rates = await hallucination_rates_by_pipeline(db, [str(p.id) for p in owned_pipelines])
        total_cost = 0.0
        for p in owned_pipelines:
            total_cost += estimate_hallucination_cost(
                queries_per_month=int(p.queries_per_month or DEFAULT_QUERIES_PER_MONTH),
                cost_per_wrong_answer_usd=float(
                    p.cost_per_wrong_answer_usd
                    if p.cost_per_wrong_answer_usd is not None
                    else DEFAULT_COST_PER_WRONG_ANSWER_USD
                ),
                hallucination_rate_value=rates.get(str(p.id), 0.0),
            )
        hallucination_cost_usd = round(total_cost, 2)
        if len(owned_pipelines) == 1:
            only = owned_pipelines[0]
            cost_pipeline_id = str(only.id)
            queries_per_month = int(only.queries_per_month or DEFAULT_QUERIES_PER_MONTH)
            cost_per_wrong = float(
                only.cost_per_wrong_answer_usd
                if only.cost_per_wrong_answer_usd is not None
                else DEFAULT_COST_PER_WRONG_ANSWER_USD
            )
        else:
            queries_per_month = sum(
                int(p.queries_per_month or DEFAULT_QUERIES_PER_MONTH) for p in owned_pipelines
            )
            cost_per_wrong = DEFAULT_COST_PER_WRONG_ANSWER_USD

    from app.services.bm25_metrics import build_bm25_aggregate

    bm25_agg = await build_bm25_aggregate(
        db,
        current_user,
        pipeline_id=pipeline_id,
        pipeline_ids=[str(pid) for pid in pipeline_ids],
    )

    return DashboardMetrics(
        total_queries=total,
        hallucination_rate=round(hall_count / total if total > 0 else 0, 3),
        mean_faithfulness=round(float(row[1] or 0), 3),
        mean_context_precision=round(float(row[2] or 0), 3),
        trustworthiness_score=trustworthiness_score,
        queries_today=today_count,
        queries_this_week=week_count,
        failure_type_counts=failure_counts,
        recent_failures=recent_failures,
        recent_recommendations=recent_recommendations,
        queries_trend_pct=percent_change(float(curr_count), float(prev_count)),
        hallucination_rate_trend_pct=percent_change(curr_hall_rate, prev_hall_rate),
        faithfulness_trend_pct=percent_change(curr_faith, prev_faith),
        hallucination_cost_usd=hallucination_cost_usd,
        queries_per_month=queries_per_month,
        cost_per_wrong_answer_usd=cost_per_wrong,
        cost_pipeline_id=cost_pipeline_id,
        bm25_outperform_rate=bm25_agg.get("bm25_outperform_rate"),
        bm25_traces_compared=int(bm25_agg.get("traces_compared") or 0),
        bm25_summary=bm25_agg.get("summary"),
    )
