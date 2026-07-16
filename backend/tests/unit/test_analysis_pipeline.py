"""
Deterministic analysis pipeline tests (grounding → classify → persist).

ML is faked — no torch / NLI / LLM network calls.
"""
from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.session import Base
from app.models.models import (
    AnalysisJob,
    ChunkStat,
    FailureType,
    GroundingResult,
    JobStatus,
    Pipeline,
    QueryTrace,
    RetrievedChunk,
    User,
)


def _engine():
    return create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def _seed_trace(
    session: Session,
    *,
    answer: str,
    chunks: list[dict],
    query: str = "What is OAuth token refresh?",
) -> str:
    user = User(
        id=str(uuid.uuid4()),
        email=f"analysis+{uuid.uuid4().hex}@example.com",
        password_hash="hash",
        name="Analyst",
    )
    session.add(user)
    session.flush()

    pipeline = Pipeline(
        id=str(uuid.uuid4()),
        user_id=user.id,
        name="analysis-pipeline",
    )
    session.add(pipeline)
    session.flush()

    trace = QueryTrace(
        id=str(uuid.uuid4()),
        pipeline_id=pipeline.id,
        query_text=query,
        answer_text=answer,
        analysis_status="pending",
    )
    session.add(trace)
    session.flush()

    for i, c in enumerate(chunks):
        session.add(
            RetrievedChunk(
                id=str(uuid.uuid4()),
                trace_id=trace.id,
                chunk_id=c["chunk_id"],
                chunk_text=c["chunk_text"],
                similarity_score=c.get("similarity_score", 0.8),
                rank=c.get("rank", i + 1),
                was_cited=False,
            )
        )
        session.add(
            ChunkStat(
                id=str(uuid.uuid4()),
                chunk_id=c["chunk_id"],
                pipeline_id=pipeline.id,
                text=c["chunk_text"],
                retrieval_count=c.get("retrieval_count", 1),
                citation_count=0,
                citation_rate=0.0,
            )
        )

    session.add(
        AnalysisJob(
            id=str(uuid.uuid4()),
            trace_id=trace.id,
            status=JobStatus.pending,
        )
    )
    session.commit()
    return trace.id


def _fake_grounding_grounded():
    return {
        "grounded_fraction": 1.0,
        "is_hallucination": False,
        "sentence_results": [
            {
                "sentence_text": "OAuth refresh uses a refresh token.",
                "sentence_index": 0,
                "is_grounded": True,
                "supporting_chunk_id": "c1",
                "confidence_score": 0.91,
            }
        ],
    }


def _fake_grounding_hallucination():
    return {
        "grounded_fraction": 0.0,
        "is_hallucination": True,
        "sentence_results": [
            {
                "sentence_text": "The moon is made of cheese.",
                "sentence_index": 0,
                "is_grounded": False,
                "supporting_chunk_id": None,
                "confidence_score": 0.1,
            }
        ],
    }


async def _fake_ragas_metrics(*args, **kwargs):
    return {
        "faithfulness_score": 0.9,
        "answer_relevance_score": 0.85,
        "context_precision_score": 0.8,
        "context_recall_score": 0.75,
    }


async def _fake_ragas_low_faithfulness(*args, **kwargs):
    return {
        "faithfulness_score": 0.2,
        "answer_relevance_score": 0.5,
        "context_precision_score": 0.7,
        "context_recall_score": 0.6,
    }


def _fake_bm25(query, chunks):
    scored = []
    for c in chunks:
        item = dict(c)
        item["bm25_score"] = 0.7
        scored.append(item)
    return {
        "bm25_better": False,
        "top_vector_score": 0.8,
        "top_bm25_score": 0.7,
        "comparable": True,
        "analysis": "Vector search performed well for this query",
        "chunks_with_bm25": scored,
    }


@pytest.fixture
def analysis_env():
    engine = _engine()
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    with patch("app.db.session.sync_engine", engine):
        yield engine, SessionLocal

    Base.metadata.drop_all(engine)
    engine.dispose()


def _run_analysis(trace_id: str):
    from app.workers.tasks import run_analysis

    # Call Celery task body directly (no broker).
    return run_analysis.run(trace_id)


def test_analysis_persists_grounding_metrics_and_status(analysis_env):
    engine, SessionLocal = analysis_env
    with SessionLocal() as session:
        trace_id = _seed_trace(
            session,
            answer="OAuth refresh uses a refresh token.",
            chunks=[
                {
                    "chunk_id": "c1",
                    "chunk_text": "OAuth token refresh uses the refresh_token grant.",
                    "similarity_score": 0.9,
                }
            ],
        )

    with (
        patch("app.services.grounding.check_grounding", return_value=_fake_grounding_grounded()),
        patch("app.services.bm25_service.get_bm25_comparison", side_effect=_fake_bm25),
        patch(
            "app.services.ragas_service.compute_all_metrics",
            new_callable=AsyncMock,
            side_effect=_fake_ragas_metrics,
        ),
        patch("app.services.slack_alerts.send_hallucination_alert_sync"),
    ):
        _run_analysis(trace_id)

    with SessionLocal() as session:
        trace = session.get(QueryTrace, trace_id)
        assert trace is not None
        assert trace.analysis_status == "completed"
        assert trace.grounded_fraction == 1.0
        assert trace.is_hallucination is False
        assert trace.faithfulness_score == 0.9
        assert trace.context_precision_score == 0.8
        assert trace.context_recall_score == 0.75
        assert trace.answer_relevance_score == 0.85
        assert trace.trustworthiness_score is not None and trace.trustworthiness_score > 0
        assert trace.failure_type in {FailureType.none, "none", None} or (
            getattr(trace.failure_type, "value", trace.failure_type) == "none"
        )

        grounding_rows = (
            session.query(GroundingResult)
            .filter(GroundingResult.trace_id == trace_id)
            .all()
        )
        assert len(grounding_rows) == 1
        assert grounding_rows[0].is_grounded is True
        assert grounding_rows[0].supporting_chunk_id == "c1"

        chunk = (
            session.query(RetrievedChunk)
            .filter(RetrievedChunk.trace_id == trace_id)
            .one()
        )
        assert chunk.was_cited is True
        assert chunk.bm25_score == 0.7

        cs = (
            session.query(ChunkStat)
            .filter(ChunkStat.chunk_id == "c1")
            .one()
        )
        assert cs.citation_count == 1
        assert cs.citation_rate == 1.0

        job = session.query(AnalysisJob).filter(AnalysisJob.trace_id == trace_id).one()
        assert job.status == JobStatus.completed
        assert job.completed_at is not None


def test_analysis_classifies_hallucination_and_persists(analysis_env):
    engine, SessionLocal = analysis_env
    with SessionLocal() as session:
        trace_id = _seed_trace(
            session,
            answer="The moon is made of cheese.",
            chunks=[
                {
                    "chunk_id": "c1",
                    "chunk_text": "OAuth token refresh documentation.",
                    "similarity_score": 0.85,
                }
            ],
        )

    with (
        patch(
            "app.services.grounding.check_grounding",
            return_value=_fake_grounding_hallucination(),
        ),
        patch("app.services.bm25_service.get_bm25_comparison", side_effect=_fake_bm25),
        patch(
            "app.services.ragas_service.compute_all_metrics",
            new_callable=AsyncMock,
            side_effect=_fake_ragas_low_faithfulness,
        ),
        patch("app.services.slack_alerts.send_hallucination_alert_sync") as slack,
    ):
        _run_analysis(trace_id)

    with SessionLocal() as session:
        trace = session.get(QueryTrace, trace_id)
        assert trace.analysis_status == "completed"
        assert trace.is_hallucination is True
        assert trace.grounded_fraction == 0.0
        failure = getattr(trace.failure_type, "value", trace.failure_type)
        assert failure == "hallucination"
        assert trace.failure_explanation

        grounding_rows = (
            session.query(GroundingResult)
            .filter(GroundingResult.trace_id == trace_id)
            .all()
        )
        assert len(grounding_rows) == 1
        assert grounding_rows[0].is_grounded is False


def test_analysis_missing_trace_is_noop(analysis_env):
    with (
        patch("app.services.grounding.check_grounding") as grounding,
        patch("app.services.ragas_service.compute_all_metrics", new_callable=AsyncMock) as ragas,
    ):
        _run_analysis(str(uuid.uuid4()))
        grounding.assert_not_called()
        ragas.assert_not_called()


def test_analysis_falls_back_when_ragas_fails(analysis_env):
    """RAGAS failure is soft; heuristic context recall + grounding still persist."""
    engine, SessionLocal = analysis_env
    with SessionLocal() as session:
        trace_id = _seed_trace(
            session,
            answer="OAuth refresh uses a refresh token.",
            chunks=[
                {
                    "chunk_id": "c1",
                    "chunk_text": "OAuth token refresh uses the refresh_token grant.",
                    "similarity_score": 0.9,
                }
            ],
        )

    with (
        patch("app.services.grounding.check_grounding", return_value=_fake_grounding_grounded()),
        patch("app.services.bm25_service.get_bm25_comparison", side_effect=_fake_bm25),
        patch(
            "app.services.ragas_service.compute_all_metrics",
            new_callable=AsyncMock,
            side_effect=RuntimeError("llm down"),
        ),
        patch(
            "app.services.context_recall.compute_context_recall_heuristic",
            return_value=0.66,
        ),
        patch("app.services.slack_alerts.send_hallucination_alert_sync"),
    ):
        _run_analysis(trace_id)

    with SessionLocal() as session:
        trace = session.get(QueryTrace, trace_id)
        assert trace.analysis_status == "completed"
        assert trace.grounded_fraction == 1.0
        assert trace.context_recall_score == 0.66
        assert session.query(GroundingResult).filter(GroundingResult.trace_id == trace_id).count() == 1


def test_analysis_soft_fails_bm25_and_grounding(analysis_env):
    engine, SessionLocal = analysis_env
    with SessionLocal() as session:
        trace_id = _seed_trace(
            session,
            answer="OAuth refresh uses a refresh token.",
            chunks=[
                {
                    "chunk_id": "c1",
                    "chunk_text": "OAuth token refresh uses the refresh_token grant.",
                    "similarity_score": 0.9,
                }
            ],
        )

    with (
        patch(
            "app.services.bm25_service.get_bm25_comparison",
            side_effect=RuntimeError("bm25 boom"),
        ),
        patch(
            "app.services.grounding.check_grounding",
            side_effect=RuntimeError("nli boom"),
        ),
        patch(
            "app.services.ragas_service.compute_all_metrics",
            new_callable=AsyncMock,
            side_effect=_fake_ragas_metrics,
        ),
        patch("app.services.slack_alerts.send_hallucination_alert_sync"),
    ):
        _run_analysis(trace_id)

    with SessionLocal() as session:
        trace = session.get(QueryTrace, trace_id)
        assert trace.analysis_status == "completed"
        assert trace.grounded_fraction is None


def test_analysis_sends_slack_on_hallucination(analysis_env):
    engine, SessionLocal = analysis_env
    with SessionLocal() as session:
        trace_id = _seed_trace(
            session,
            answer="The moon is made of cheese.",
            chunks=[
                {
                    "chunk_id": "c1",
                    "chunk_text": "OAuth token refresh uses the refresh_token grant.",
                    "similarity_score": 0.85,
                }
            ],
        )
        trace = session.get(QueryTrace, trace_id)
        user = session.get(User, session.get(Pipeline, trace.pipeline_id).user_id)
        user.slack_alert_enabled = True
        user.slack_webhook_url = "https://hooks.slack.com/services/T/B/X"
        session.commit()

    with (
        patch(
            "app.services.grounding.check_grounding",
            return_value=_fake_grounding_hallucination(),
        ),
        patch("app.services.bm25_service.get_bm25_comparison", side_effect=_fake_bm25),
        patch(
            "app.services.ragas_service.compute_all_metrics",
            new_callable=AsyncMock,
            side_effect=_fake_ragas_low_faithfulness,
        ),
        patch("app.services.slack_alerts.send_hallucination_alert_sync") as slack,
    ):
        _run_analysis(trace_id)
        slack.assert_called_once()


def test_analysis_generates_fix_recommendations_on_coverage_gap(analysis_env):
    engine, SessionLocal = analysis_env
    with SessionLocal() as session:
        trace_id = _seed_trace(
            session,
            answer="Something unrelated.",
            chunks=[
                {
                    "chunk_id": "c1",
                    "chunk_text": "totally unrelated corpus text",
                    "similarity_score": 0.1,
                }
            ],
        )
        trace = session.get(QueryTrace, trace_id)
        # Prior coverage_gap history so recommendations have input queries
        session.add(
            QueryTrace(
                id=str(uuid.uuid4()),
                pipeline_id=trace.pipeline_id,
                query_text="What is OAuth token refresh?",
                answer_text="unknown",
                analysis_status="completed",
                failure_type=FailureType.coverage_gap,
            )
        )
        session.add(
            QueryTrace(
                id=str(uuid.uuid4()),
                pipeline_id=trace.pipeline_id,
                query_text="How does refresh token rotation work?",
                answer_text="unknown",
                analysis_status="completed",
                failure_type=FailureType.retrieval_miss,
            )
        )
        session.commit()

    def _bm25_better(query, chunks):
        result = _fake_bm25(query, chunks)
        result["bm25_better"] = True
        return result

    with (
        patch("app.services.grounding.check_grounding", return_value=_fake_grounding_grounded()),
        patch("app.services.bm25_service.get_bm25_comparison", side_effect=_bm25_better),
        patch(
            "app.services.ragas_service.compute_all_metrics",
            new_callable=AsyncMock,
            side_effect=_fake_ragas_metrics,
        ),
        patch(
            "app.services.fix_recommendations.generate_fix_recommendations",
            return_value=[
                {
                    "recommendation_type": "add_docs",
                    "topic_description": "oauth",
                    "affected_query_count": 2,
                    "sample_queries": ["What is OAuth token refresh?"],
                }
            ],
        ),
        patch(
            "app.services.fix_recommendations.generate_k_increase_recommendation",
            return_value={
                "recommendation_type": "increase_k",
                "topic_description": "retrieval",
                "affected_query_count": 2,
                "sample_queries": [],
            },
        ),
        patch(
            "app.services.fix_recommendations.generate_retrieval_recommendation",
            return_value={
                "recommendation_type": "hybrid_bm25",
                "topic_description": "hybrid",
                "affected_query_count": 10,
                "sample_queries": [],
            },
        ),
        patch("app.services.slack_alerts.send_hallucination_alert_sync"),
    ):
        _run_analysis(trace_id)

    with SessionLocal() as session:
        trace = session.get(QueryTrace, trace_id)
        assert trace.analysis_status == "completed"
        assert getattr(trace.failure_type, "value", trace.failure_type) == "coverage_gap"
        from app.models.models import FixRecommendation

        assert session.query(FixRecommendation).count() >= 1


def test_analysis_slack_alert_exception_is_soft(analysis_env):
    engine, SessionLocal = analysis_env
    with SessionLocal() as session:
        trace_id = _seed_trace(
            session,
            answer="The moon is made of cheese.",
            chunks=[
                {
                    "chunk_id": "c1",
                    "chunk_text": "OAuth token refresh uses the refresh_token grant.",
                    "similarity_score": 0.85,
                }
            ],
        )
        trace = session.get(QueryTrace, trace_id)
        user = session.get(User, session.get(Pipeline, trace.pipeline_id).user_id)
        user.slack_alert_enabled = True
        user.slack_webhook_url = "https://hooks.slack.com/services/T/B/X"
        session.commit()

    with (
        patch(
            "app.services.grounding.check_grounding",
            return_value=_fake_grounding_hallucination(),
        ),
        patch("app.services.bm25_service.get_bm25_comparison", side_effect=_fake_bm25),
        patch(
            "app.services.ragas_service.compute_all_metrics",
            new_callable=AsyncMock,
            side_effect=_fake_ragas_low_faithfulness,
        ),
        patch(
            "app.services.slack_alerts.send_hallucination_alert_sync",
            side_effect=RuntimeError("slack boom"),
        ),
    ):
        _run_analysis(trace_id)

    with SessionLocal() as session:
        assert session.get(QueryTrace, trace_id).analysis_status == "completed"


def test_analysis_ragas_and_heuristic_both_fail(analysis_env):
    engine, SessionLocal = analysis_env
    with SessionLocal() as session:
        trace_id = _seed_trace(
            session,
            answer="OAuth refresh uses a refresh token.",
            chunks=[
                {
                    "chunk_id": "c1",
                    "chunk_text": "OAuth token refresh uses the refresh_token grant.",
                    "similarity_score": 0.9,
                }
            ],
        )

    with (
        patch("app.services.grounding.check_grounding", return_value=_fake_grounding_grounded()),
        patch("app.services.bm25_service.get_bm25_comparison", side_effect=_fake_bm25),
        patch(
            "app.services.ragas_service.compute_all_metrics",
            new_callable=AsyncMock,
            side_effect=RuntimeError("llm down"),
        ),
        patch(
            "app.services.context_recall.compute_context_recall_heuristic",
            side_effect=RuntimeError("heuristic boom"),
        ),
        patch("app.services.slack_alerts.send_hallucination_alert_sync"),
    ):
        _run_analysis(trace_id)

    with SessionLocal() as session:
        assert session.get(QueryTrace, trace_id).analysis_status == "completed"


def test_analysis_marks_failed_and_retries_on_hard_error(analysis_env):
    engine, SessionLocal = analysis_env
    with SessionLocal() as session:
        trace_id = _seed_trace(
            session,
            answer="OAuth refresh uses a refresh token.",
            chunks=[
                {
                    "chunk_id": "c1",
                    "chunk_text": "OAuth token refresh uses the refresh_token grant.",
                    "similarity_score": 0.9,
                }
            ],
        )

    with (
        patch("app.services.grounding.check_grounding", return_value=_fake_grounding_grounded()),
        patch("app.services.bm25_service.get_bm25_comparison", side_effect=_fake_bm25),
        patch(
            "app.services.ragas_service.compute_all_metrics",
            new_callable=AsyncMock,
            side_effect=_fake_ragas_metrics,
        ),
        patch(
            "app.services.failure_classifier.classify_failure",
            side_effect=RuntimeError("classify boom"),
        ),
    ):
        with pytest.raises(Exception):
            _run_analysis(trace_id)

    with SessionLocal() as session:
        trace = session.get(QueryTrace, trace_id)
        assert trace.analysis_status == "failed"
        job = session.query(AnalysisJob).filter(AnalysisJob.trace_id == trace_id).one()
        assert job.status == JobStatus.failed
        assert "classify boom" in (job.error_message or "")
