"""Knowledge gap detection + clustering (Phase 10.1 / PRD v3).

Reuses HDBSCAN clustering from fix_recommendations; persists richer gap rows.
"""

from __future__ import annotations

import json
from typing import Any

import structlog

from app.services.fix_recommendations import generate_fix_recommendations

logger = structlog.get_logger()

_GAP_STATUSES = frozenset({"open", "acknowledged", "in_progress", "fixed"})
_PRIORITIES = frozenset({"critical", "high", "medium", "low"})


def priority_for_count(query_count: int) -> str:
    if query_count >= 20:
        return "critical"
    if query_count >= 10:
        return "high"
    if query_count >= 5:
        return "medium"
    return "low"


def detect_knowledge_gaps(
    coverage_gap_queries: list[dict],
    *,
    min_cluster_size: int = 3,
    pipeline_queries_per_month: int = 10000,
    cost_per_wrong_answer_usd: float = 5.0,
    total_recent_failures: int | None = None,
) -> list[dict[str, Any]]:
    """
    Cluster coverage-gap queries into knowledge gap records.

    ``coverage_gap_queries`` items need ``query_text``.
    """
    if len(coverage_gap_queries) < min_cluster_size:
        return []

    recommendations = generate_fix_recommendations(
        coverage_gap_queries,
        min_cluster_size=min_cluster_size,
    )
    denom = total_recent_failures or len(coverage_gap_queries) or 1
    gaps: list[dict[str, Any]] = []

    for rec in recommendations:
        if rec.get("recommendation_type") != "coverage_gap":
            continue
        raw_samples = rec.get("sample_queries") or "[]"
        if isinstance(raw_samples, str):
            try:
                samples = json.loads(raw_samples)
            except json.JSONDecodeError:
                samples = []
        else:
            samples = list(raw_samples)

        count = int(rec.get("affected_query_count") or 0)
        representative = (
            samples[0] if samples else rec.get("topic_description") or "coverage gap"
        )[:2000]
        topic_label = representative[:500]
        failure_rate = min(1.0, count / float(denom))
        estimated_cost = failure_rate * pipeline_queries_per_month * cost_per_wrong_answer_usd

        gaps.append(
            {
                "topic_label": topic_label,
                "representative_query": representative,
                "query_count": count,
                "failure_rate": round(failure_rate, 4),
                "affected_users_estimate": count,
                "estimated_monthly_cost_usd": round(estimated_cost, 2),
                "priority": priority_for_count(count),
                "suggested_document_topic": (f"Add documentation covering: {topic_label[:200]}"),
                "status": "open",
            }
        )

    gaps.sort(key=lambda g: g["query_count"], reverse=True)
    return gaps


def upsert_knowledge_gaps(db, pipeline, gap_dicts: list[dict[str, Any]]) -> int:
    """Insert or refresh open gaps by (pipeline_id, topic_label). Returns rows touched."""
    from datetime import datetime, timezone

    from app.models.models import KnowledgeGap

    touched = 0
    now = datetime.now(timezone.utc)
    for gap in gap_dicts:
        topic = gap["topic_label"][:500]
        existing = (
            db.query(KnowledgeGap)
            .filter(
                KnowledgeGap.pipeline_id == pipeline.id,
                KnowledgeGap.topic_label == topic,
                KnowledgeGap.status.in_(("open", "acknowledged", "in_progress")),
            )
            .first()
        )
        if existing:
            existing.query_count = gap["query_count"]
            existing.representative_query = gap.get("representative_query")
            existing.failure_rate = gap.get("failure_rate")
            existing.affected_users_estimate = gap.get("affected_users_estimate") or 0
            existing.estimated_monthly_cost_usd = gap.get("estimated_monthly_cost_usd")
            existing.priority = gap.get("priority") or existing.priority
            existing.suggested_document_topic = gap.get("suggested_document_topic")
            existing.updated_at = now
            touched += 1
            continue

        db.add(
            KnowledgeGap(
                pipeline_id=pipeline.id,
                topic_label=topic,
                representative_query=gap.get("representative_query"),
                query_count=gap["query_count"],
                failure_rate=gap.get("failure_rate"),
                affected_users_estimate=gap.get("affected_users_estimate") or 0,
                estimated_monthly_cost_usd=gap.get("estimated_monthly_cost_usd"),
                priority=gap.get("priority") or "medium",
                suggested_document_topic=gap.get("suggested_document_topic"),
                status="open",
                created_at=now,
                updated_at=now,
            )
        )
        touched += 1
    return touched


def normalize_gap_status(value: str) -> str:
    status = (value or "").strip().lower()
    if status not in _GAP_STATUSES:
        raise ValueError(f"status must be one of {sorted(_GAP_STATUSES)}")
    return status
