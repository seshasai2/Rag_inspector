"""Regression severity + pre-deploy (Phase 10.5)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.regression import (
    classify_severity,
    compare_metrics,
    create_snapshot,
    metrics_from_traces,
    pre_deploy_result,
)


def test_classify_severity_bands():
    assert classify_severity(0) == "none"
    assert classify_severity(-1.5) == "none"
    assert classify_severity(-3) == "minor"
    assert classify_severity(-7) == "major"
    assert classify_severity(-12) == "critical"


def test_compare_metrics_detects_regression():
    baseline = {
        "trust_score": 80.0,
        "faithfulness_avg": 0.9,
        "hallucination_rate": 0.05,
    }
    current = {
        "trust_score": 68.0,
        "faithfulness_avg": 0.8,
        "hallucination_rate": 0.08,
    }
    delta = compare_metrics(baseline, current)
    assert delta["trust_score_delta"] == -12.0
    assert delta["regression_severity"] == "critical"
    assert delta["is_regression"] is True


def test_pre_deploy_blocks_on_major():
    baseline = {"trust_score": 80.0, "faithfulness_avg": 0.9, "hallucination_rate": 0.05}
    current = {"trust_score": 72.0, "faithfulness_avg": 0.85, "hallucination_rate": 0.06}
    result = pre_deploy_result(baseline, current)
    assert result["passed"] is False
    assert result["regression_severity"] == "major"
    assert result["blocking_issues"]


def test_pre_deploy_passes_stable():
    baseline = {"trust_score": 80.0, "faithfulness_avg": 0.9, "hallucination_rate": 0.05}
    current = {"trust_score": 79.0, "faithfulness_avg": 0.9, "hallucination_rate": 0.05}
    result = pre_deploy_result(baseline, current)
    assert result["passed"] is True
    assert result["regression_risk"] == "low"


def test_metrics_from_traces():
    traces = [
        SimpleNamespace(
            faithfulness_score=1.0,
            grounded_fraction=1.0,
            context_precision_score=1.0,
            is_hallucination=False,
        ),
        SimpleNamespace(
            faithfulness_score=0.8,
            grounded_fraction=0.8,
            context_precision_score=0.8,
            is_hallucination=True,
        ),
    ]
    m = metrics_from_traces(traces)
    assert m["trace_count"] == 2
    assert m["hallucination_rate"] == 0.5
    assert m["trust_score"] >= 0


def test_create_snapshot_persists():
    db = MagicMock()
    db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = []
    snap = create_snapshot(db, "pipe-1", snapshot_label="v1")
    assert db.add.called
    assert snap.snapshot_label == "v1"
    assert snap.trust_score == 0.0
