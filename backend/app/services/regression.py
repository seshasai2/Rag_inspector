"""Regression snapshots + severity classification (Phase 10.5)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.models.models import QueryTrace, RegressionSnapshot
from app.services.monitoring import hallucination_rate
from app.services.trust_scorer import TRUST_SCORE_WINDOW, compute_trust_score


def _mean(values: list[float | None]) -> float | None:
    present = [float(v) for v in values if v is not None]
    if not present:
        return None
    return round(sum(present) / len(present), 4)


def metrics_from_traces(traces: list) -> dict[str, Any]:
    trust = float(compute_trust_score(traces)) if traces else 0.0
    return {
        "trust_score": trust,
        "faithfulness_avg": _mean([t.faithfulness_score for t in traces]),
        "context_precision_avg": _mean([t.context_precision_score for t in traces]),
        "hallucination_rate": round(hallucination_rate(traces), 4) if traces else 0.0,
        "trace_count": len(traces),
    }


def load_recent_traces(db: Session, pipeline_id: str) -> list:
    return (
        db.query(QueryTrace)
        .filter(QueryTrace.pipeline_id == pipeline_id)
        .order_by(QueryTrace.traced_at.desc())
        .limit(TRUST_SCORE_WINDOW)
        .all()
    )


def create_snapshot(
    db: Session,
    pipeline_id: str,
    *,
    snapshot_label: str | None = None,
    now: datetime | None = None,
) -> RegressionSnapshot:
    now = now or datetime.now(timezone.utc)
    traces = load_recent_traces(db, pipeline_id)
    metrics = metrics_from_traces(traces)
    snap = RegressionSnapshot(
        pipeline_id=pipeline_id,
        snapshot_label=snapshot_label,
        trust_score=metrics["trust_score"],
        faithfulness_avg=metrics["faithfulness_avg"],
        context_precision_avg=metrics["context_precision_avg"],
        hallucination_rate=metrics["hallucination_rate"],
        trace_count=metrics["trace_count"],
        snapshot_at=now,
    )
    db.add(snap)
    db.flush()
    return snap


def snapshot_to_dict(snap: RegressionSnapshot | dict[str, Any]) -> dict[str, Any]:
    if isinstance(snap, dict):
        return snap
    return {
        "id": str(snap.id),
        "pipeline_id": str(snap.pipeline_id),
        "snapshot_label": snap.snapshot_label,
        "trust_score": snap.trust_score,
        "faithfulness_avg": snap.faithfulness_avg,
        "context_precision_avg": snap.context_precision_avg,
        "hallucination_rate": snap.hallucination_rate,
        "trace_count": snap.trace_count,
        "snapshot_at": snap.snapshot_at,
    }


def classify_severity(trust_delta: float) -> str:
    """trust_delta = current - baseline (negative means regression)."""
    if trust_delta > -2.0:
        return "none"
    if trust_delta > -5.0:
        return "minor"
    if trust_delta > -10.0:
        return "major"
    return "critical"


def recommendation_for(severity: str) -> str:
    return {
        "none": "No significant trust regression vs baseline.",
        "minor": "Minor trust drop — review recent hallucinations before deploy.",
        "major": "Major trust regression — investigate retrieval/prompt changes.",
        "critical": "Critical trust drop — block deploy until metrics recover.",
    }[severity]


def compare_metrics(baseline: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    trust_delta = round(float(current["trust_score"]) - float(baseline["trust_score"]), 2)
    faith_b = baseline.get("faithfulness_avg")
    faith_c = current.get("faithfulness_avg")
    faith_delta = (
        None if faith_b is None or faith_c is None else round(float(faith_c) - float(faith_b), 4)
    )
    hall_b = baseline.get("hallucination_rate")
    hall_c = current.get("hallucination_rate")
    hall_delta = (
        None if hall_b is None or hall_c is None else round(float(hall_c) - float(hall_b), 4)
    )
    severity = classify_severity(trust_delta)
    return {
        "trust_score_delta": trust_delta,
        "faithfulness_delta": faith_delta,
        "hallucination_rate_delta": hall_delta,
        "is_regression": severity != "none",
        "regression_severity": severity,
        "recommendation": recommendation_for(severity),
    }


def regression_risk(severity: str) -> str:
    return {
        "none": "low",
        "minor": "medium",
        "major": "high",
        "critical": "high",
    }[severity]


def pre_deploy_result(
    baseline: dict[str, Any],
    current: dict[str, Any],
) -> dict[str, Any]:
    delta = compare_metrics(baseline, current)
    severity = delta["regression_severity"]
    blocking: list[str] = []
    if severity in {"major", "critical"}:
        blocking.append(
            f"Trust score regression ({delta['trust_score_delta']}) severity={severity}"
        )
    hall_delta = delta.get("hallucination_rate_delta")
    if hall_delta is not None and hall_delta >= 0.05:
        blocking.append("Hallucination rate increased by ≥5 percentage points")
    passed = len(blocking) == 0
    return {
        "passed": passed,
        "trust_score": current["trust_score"],
        "baseline_trust_score": baseline["trust_score"],
        "regression_risk": regression_risk(severity),
        "blocking_issues": blocking,
        "regression_severity": severity,
        "delta": delta,
    }
