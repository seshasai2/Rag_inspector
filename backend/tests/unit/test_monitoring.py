"""Monitoring probe evaluation (Phase 10.4)."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.monitoring import (
    build_alerts,
    count_probe_failures,
    evaluate_pipeline_monitoring,
    hallucination_rate,
)


def test_hallucination_rate():
    traces = [
        SimpleNamespace(is_hallucination=True),
        SimpleNamespace(is_hallucination=False),
        SimpleNamespace(is_hallucination=True),
    ]
    assert hallucination_rate(traces) == 2 / 3


def test_build_alerts():
    alerts = build_alerts(trust=50, hall_rate=0.2, trust_threshold=70, hall_threshold=0.1)
    types = {a["type"] for a in alerts}
    assert types == {"trust_score", "hallucination_rate"}


def test_count_probe_failures_keyword_match():
    traces = [
        SimpleNamespace(
            query_text="how do I get a refund on annual plan",
            is_hallucination=True,
            failure_type="coverage_gap",
        ),
        SimpleNamespace(query_text="hello world", is_hallucination=False, failure_type="none"),
    ]
    run, failed = count_probe_failures(traces, ["refund policy"])
    assert run == 1
    assert failed == 1


def test_evaluate_pipeline_monitoring_persists_run():
    config = MagicMock()
    config.id = "cfg-1"
    config.pipeline_id = "pipe-1"
    config.probe_queries = '["refund"]'
    config.alert_trust_threshold = 70.0
    config.alert_hallucination_threshold = 0.1
    config.interval_minutes = 30

    trace = SimpleNamespace(
        query_text="refund window",
        is_hallucination=False,
        failure_type="none",
        faithfulness_score=0.9,
        grounded_fraction=0.9,
        context_precision_score=0.8,
        traced_at=None,
    )

    db = MagicMock()
    query = db.query.return_value
    # First query: traces; second query: previous run
    filter_chain = query.filter.return_value
    filter_chain.order_by.return_value.limit.return_value.all.return_value = [trace]
    filter_chain.order_by.return_value.first.return_value = None

    run = evaluate_pipeline_monitoring(db, config)
    assert db.add.called
    assert run.probes_run == 1
    assert config.next_run_at is not None
    assert config.last_run_at is not None
