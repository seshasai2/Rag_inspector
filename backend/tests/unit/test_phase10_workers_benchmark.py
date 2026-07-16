"""Coverage for Phase 10 Celery workers + retrieval benchmark (sync SQLAlchemy)."""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from app.services import retrieval_benchmark as rb
from app.workers import freshness_worker as fw
from app.workers import monitoring_worker as mw


def _chunk(*, text="alpha beta", sim=0.9, bm25=None):
    return SimpleNamespace(
        chunk_id="c1",
        chunk_text=text,
        similarity_score=sim,
        bm25_score=bm25,
    )


def test_run_retrieval_benchmark_empty_pipeline():
    db = MagicMock()
    (
        db.query.return_value.options.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value
    ) = []
    out = rb.run_retrieval_benchmark(db, "pipe-1", limit=10)
    assert out["traces_evaluated"] == 0
    assert out["bm25_win_rate"] == 0.0
    assert "Vector retrieval" in out["recommendation"]


def test_run_retrieval_benchmark_skips_empty_and_computes_bm25():
    empty = SimpleNamespace(id="t0", query_text="q", retrieved_chunks=[])
    no_query = SimpleNamespace(id="t1", query_text="", retrieved_chunks=[_chunk()])
    needs_bm25 = SimpleNamespace(
        id="t2",
        query_text="refund policy annual",
        retrieved_chunks=[_chunk(text="refund policy details", sim=0.5, bm25=None)],
    )
    with_scores = SimpleNamespace(
        id="t3",
        query_text="refund policy",
        retrieved_chunks=[
            _chunk(text="refund policy annual plan", sim=0.2, bm25=12.0),
            _chunk(text="unrelated weather", sim=0.9, bm25=0.1),
        ],
    )
    (
        db := MagicMock()
    )
    (
        db.query.return_value.options.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value
    ) = [empty, no_query, needs_bm25, with_scores]
    out = rb.run_retrieval_benchmark(db, "pipe-1")
    assert out["pipeline_id"] == "pipe-1"
    assert out["traces_evaluated"] >= 1
    assert isinstance(out["samples"], list)


def test_run_retrieval_benchmark_tie_and_vector_win_paths():
    trace = SimpleNamespace(
        id="t1",
        query_text="hello world",
        retrieved_chunks=[_chunk(bm25=1.0)],
    )
    db = MagicMock()
    (
        db.query.return_value.options.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value
    ) = [trace, trace, trace]

    summaries = [
        {
            "comparable": True,
            "bm25_better": True,
            "top_bm25_score": 2.0,
            "top_vector_score": 0.5,
            "analysis": "bm25",
        },
        {
            "comparable": True,
            "bm25_better": False,
            "top_bm25_score": 0.1,
            "top_vector_score": 0.9,
            "analysis": "vector",
        },
        {
            "comparable": True,
            "bm25_better": False,
            "top_bm25_score": 0.5,
            "top_vector_score": 0.5,
            "analysis": "tie",
        },
    ]
    with patch.object(rb, "summarize_bm25_vs_vector", side_effect=summaries):
        out = rb.run_retrieval_benchmark(db, "p")
    assert out["traces_evaluated"] == 3
    assert out["bm25_win_rate"] == pytest.approx(1 / 3, abs=1e-3)
    assert out["vector_win_rate"] == pytest.approx(1 / 3, abs=1e-3)
    assert out["tie_rate"] == pytest.approx(1 / 3, abs=1e-3)
    assert "hybrid" in out["recommendation"].lower() or "Vector" in out["recommendation"]


def test_run_llm_comparison_empty_and_buckets():
    db = MagicMock()
    q = db.query.return_value.filter.return_value.order_by.return_value.limit.return_value
    q.all.return_value = []
    empty = rb.run_llm_comparison(db, "p")
    assert empty["traces_evaluated"] == 0
    assert "Need traces" in empty["note"]

    high = SimpleNamespace(
        faithfulness_score=0.9,
        grounded_fraction=0.8,
        is_hallucination=False,
    )
    low = SimpleNamespace(
        faithfulness_score=0.4,
        grounded_fraction=0.2,
        is_hallucination=True,
    )
    q.all.return_value = [high, low, high]
    out = rb.run_llm_comparison(db, "p")
    assert out["traces_evaluated"] == 3
    assert out["high_faithfulness_count"] == 2
    assert out["low_faithfulness_count"] == 1
    assert out["hallucination_rate_low"] == 1.0


def test_check_document_freshness_creates_gap_and_clears_alert():
    now = datetime.now(timezone.utc)
    outdated = SimpleNamespace(
        pipeline_id="p1",
        title="Old policy doc",
        freshness_status="fresh",
        freshness_alert_sent=False,
        last_modified_at=None,
        ingested_at=now,
    )
    recovering = SimpleNamespace(
        pipeline_id="p1",
        title="Recovered doc",
        freshness_status="outdated",
        freshness_alert_sent=True,
        last_modified_at=None,
        ingested_at=now,
    )

    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    doc_q = MagicMock()
    doc_q.filter.return_value = doc_q
    doc_q.all.return_value = [outdated, recovering]

    gap_q = MagicMock()
    gap_q.filter.return_value.first.return_value = None

    def _query(model):
        name = getattr(model, "__name__", str(model))
        if "KnowledgeGap" in name:
            return gap_q
        return doc_q

    session.query.side_effect = _query

    with (
        patch("app.db.session.sync_engine", MagicMock()),
        patch("sqlalchemy.orm.Session", return_value=session),
        patch(
            "app.services.document_freshness.refresh_document_freshness",
            side_effect=["outdated", "fresh"],
        ),
    ):
        result = fw.check_document_freshness(pipeline_id="p1")

    assert result["updated"] == 2
    assert result["alerts"] == 1
    assert session.commit.called
    assert outdated.freshness_alert_sent is True
    assert recovering.freshness_alert_sent is False
    assert session.add.called


def test_check_document_freshness_existing_gap_and_needs_review():
    now = datetime.now(timezone.utc)
    doc = SimpleNamespace(
        pipeline_id="p1",
        title="Critical stale",
        freshness_status="fresh",
        freshness_alert_sent=False,
        last_modified_at=None,
        ingested_at=now,
    )
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    doc_q = MagicMock()
    doc_q.all.return_value = [doc]
    gap_q = MagicMock()
    gap_q.filter.return_value.first.return_value = MagicMock()  # existing gap

    def _query(model):
        name = getattr(model, "__name__", str(model))
        if "KnowledgeGap" in name:
            return gap_q
        return doc_q

    session.query.side_effect = _query

    with (
        patch("app.db.session.sync_engine", MagicMock()),
        patch("sqlalchemy.orm.Session", return_value=session),
        patch(
            "app.services.document_freshness.refresh_document_freshness",
            return_value="needs_review",
        ),
    ):
        result = fw.check_document_freshness(pipeline_id=None)

    assert result["alerts"] == 1
    assert not session.add.called  # existing gap — no insert
    assert doc.freshness_alert_sent is True


def test_run_monitoring_probes_success_and_slack_and_failure():
    pipeline = SimpleNamespace(user_id="u1")
    config_ok = SimpleNamespace(pipeline_id="p-ok", pipeline=pipeline, is_enabled=True)
    config_fail = SimpleNamespace(pipeline_id="p-fail", pipeline=None, is_enabled=True)

    run = SimpleNamespace(
        alerts_triggered='[{"type":"trust_score"}]',
        trust_score=40.0,
        hallucination_rate=0.5,
    )
    user = SimpleNamespace(slack_alert_enabled=True, slack_webhook_url="https://hooks.example/x")

    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)

    cfg_q = MagicMock()
    cfg_q.options.return_value = cfg_q
    cfg_q.filter.return_value = cfg_q
    cfg_q.all.return_value = [config_ok, config_fail]

    user_q = MagicMock()
    user_q.filter.return_value.first.return_value = user

    def _query(model):
        name = getattr(model, "__name__", str(model))
        if "User" in name:
            return user_q
        return cfg_q

    session.query.side_effect = _query

    def _eval(_db, config, now=None):
        if config.pipeline_id == "p-fail":
            raise RuntimeError("boom")
        return run

    with (
        patch("app.db.session.sync_engine", MagicMock()),
        patch("sqlalchemy.orm.Session", return_value=session),
        patch(
            "app.services.monitoring.evaluate_pipeline_monitoring",
            side_effect=_eval,
        ),
        patch("app.services.slack_alerts.send_slack_alert_sync") as slack,
    ):
        result = mw.run_monitoring_probes(pipeline_id=None)

    assert result["ran"] == 1
    assert slack.called
    assert session.rollback.called


def test_run_monitoring_probes_forced_pipeline_no_alerts():
    config = SimpleNamespace(pipeline_id="forced-p", pipeline=None, is_enabled=True)
    run = SimpleNamespace(
        alerts_triggered="[]",
        trust_score=90.0,
        hallucination_rate=0.0,
    )
    session = MagicMock()
    session.__enter__ = MagicMock(return_value=session)
    session.__exit__ = MagicMock(return_value=False)
    cfg_q = MagicMock()
    cfg_q.options.return_value = cfg_q
    cfg_q.filter.return_value = cfg_q
    cfg_q.all.return_value = [config]
    session.query.return_value = cfg_q

    with (
        patch("app.db.session.sync_engine", MagicMock()),
        patch("sqlalchemy.orm.Session", return_value=session),
        patch(
            "app.services.monitoring.evaluate_pipeline_monitoring",
            return_value=run,
        ),
    ):
        result = mw.run_monitoring_probes(pipeline_id="forced-p")
    assert result == {"ran": 1}
    assert session.commit.called
