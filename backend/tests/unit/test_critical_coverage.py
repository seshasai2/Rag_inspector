"""
Additional unit tests to bring critical services/workers to ≥95% coverage.

Critical modules (Phase 4.5):
  grounding, failure_classifier, trust_scorer, trustworthiness_service,
  hallucination_cost, context_recall, bm25_service, chunk_quality,
  analysis_queue, metric_trends, slack_alerts, workers.tasks
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
    IntegrationWebhook,
    JobStatus,
    Pipeline,
    QueryTrace,
    User,
    WebhookDelivery,
    WeeklyExecutiveReport,
)


# ---------------------------------------------------------------------------
# analysis_queue
# ---------------------------------------------------------------------------


def test_enqueue_analysis_success():
    from app.services.analysis_queue import enqueue_analysis

    fake_task = MagicMock()
    fake_task.id = "celery-task-1"
    with patch("app.workers.tasks.run_analysis") as run:
        run.delay.return_value = fake_task
        assert enqueue_analysis("trace-1") == "celery-task-1"


def test_enqueue_analysis_failure_returns_none():
    from app.services.analysis_queue import enqueue_analysis

    with patch("app.workers.tasks.run_analysis") as run:
        run.delay.side_effect = RuntimeError("broker down")
        assert enqueue_analysis("trace-1") is None


# ---------------------------------------------------------------------------
# trustworthiness + trust_scorer edge
# ---------------------------------------------------------------------------


def test_trustworthiness_both_scores_and_aggregate():
    from app.services.trustworthiness_service import (
        aggregate_trustworthiness,
        compute_trustworthiness,
    )

    assert compute_trustworthiness(0.8, 0.5) == round((0.8 * 0.6 + 0.5 * 0.4) * 100, 1)
    assert compute_trustworthiness(0.9, None) == 90.0
    assert compute_trustworthiness(None, 0.4) == 40.0
    assert compute_trustworthiness(None, None) == 0.0
    assert aggregate_trustworthiness([], []) == 0.0
    assert aggregate_trustworthiness([0.8, 1.0], [0.5]) == round(
        ((0.9 * 0.6) + (0.5 * 0.4)) * 100, 1
    )
    assert aggregate_trustworthiness([1.0], []) == 100.0
    assert aggregate_trustworthiness([], [0.5]) == 50.0


def test_trust_score_empty_failure_window():
    from app.services.trust_scorer import compute_trust_score_from_metrics

    # Only faithfulness — failure window empty → reliability uses failure_rate 0
    score = compute_trust_score_from_metrics(
        faithfulness_scores=[1.0],
        grounded_fractions=[],
        context_precision_scores=[],
        is_hallucination_flags=[],
    )
    assert score > 0


# ---------------------------------------------------------------------------
# failure_classifier remaining branches
# ---------------------------------------------------------------------------


def test_failure_classifier_remaining_branches():
    from app.services.failure_classifier import classify_failure

    chunks_miss = [
        {"chunk_id": "c1", "chunk_text": "x", "similarity_score": 0.30},
        {"chunk_id": "c2", "chunk_text": "y", "similarity_score": 0.32},
    ]
    ft, _, _ = classify_failure(None, None, None, chunks_miss, "q", "a")
    assert ft == "retrieval_miss"

    # cited with all < 0.6 → chunking_issue
    chunks_frag = [
        {"chunk_id": "c1", "chunk_text": "x", "similarity_score": 0.55, "was_cited": True},
        {"chunk_id": "c2", "chunk_text": "y", "similarity_score": 0.52, "was_cited": True},
        {"chunk_id": "c3", "chunk_text": "z", "similarity_score": 0.51, "was_cited": True},
    ]
    ft, _, _ = classify_failure(None, None, None, chunks_frag, "q", "a")
    assert ft == "chunking_issue"

    chunks_ok = [
        {"chunk_id": "c1", "chunk_text": "x", "similarity_score": 0.8, "was_cited": True},
        {"chunk_id": "c2", "chunk_text": "y", "similarity_score": 0.75, "was_cited": True},
        {"chunk_id": "c3", "chunk_text": "z", "similarity_score": 0.7, "was_cited": False},
    ]
    ft, _, _ = classify_failure(0.2, None, 0.9, chunks_ok, "q", "a")
    assert ft == "hallucination"

    ft, _, _ = classify_failure(None, 0.1, None, chunks_ok, "q", "a")
    assert ft == "retrieval_irrelevant"

    ft, _, _ = classify_failure(0.9, 0.9, 0.9, chunks_ok, "q", "a")
    assert ft == "none"


# ---------------------------------------------------------------------------
# grounding: model path + load helpers
# ---------------------------------------------------------------------------


def test_grounding_with_fake_nli_model():
    from app.services import grounding as g

    class FakeModel:
        def predict(self, pairs, apply_softmax=True):
            # entailment high for first chunk
            return [[0.1, 0.1, 0.9] for _ in pairs]

    with patch.object(g, "get_cross_encoder", return_value=FakeModel()):
        result = g.check_grounding(
            "Paris is the capital of France. It is a large city today.",
            [{"chunk_id": "c1", "chunk_text": "Paris is the capital of France."}],
            threshold=0.5,
        )
    assert result["grounded_fraction"] == 1.0
    assert result["sentence_results"][0]["supporting_chunk_id"] == "c1"


def test_grounding_nli_failure_falls_back_to_keywords():
    from app.services import grounding as g

    class BoomModel:
        def predict(self, pairs, apply_softmax=True):
            raise RuntimeError("cuda boom")

    with patch.object(g, "get_cross_encoder", return_value=BoomModel()):
        result = g.check_grounding(
            "Paris is the capital of France.",
            [{"chunk_id": "c1", "chunk_text": "Paris is the capital of France."}],
            threshold=0.3,
        )
    assert result["sentence_results"]
    assert result["sentence_results"][0]["is_grounded"] is True


def test_grounding_short_answer_no_sentences():
    from app.services.grounding import check_grounding

    result = check_grounding("Hi.", [{"chunk_id": "c1", "chunk_text": "Hello world text."}])
    assert result["grounded_fraction"] == 1.0
    assert result["is_hallucination"] is False


def test_get_cross_encoder_success_path(monkeypatch):
    from app.services import grounding as g
    import sys

    g._cross_encoder = None

    class FakeCE:
        def __init__(self, *args, **kwargs):
            pass

    monkeypatch.setattr(sys.modules["sentence_transformers"], "CrossEncoder", FakeCE)
    model = g.get_cross_encoder()
    assert model is not None
    # cached
    assert g.get_cross_encoder() is model


def test_keyword_fallback_empty_sentence_words():
    from app.services.grounding import _keyword_fallback

    score, cid = _keyword_fallback("", [{"chunk_id": "c1", "chunk_text": "abc"}])
    assert score == 0.0
    assert cid is None


# ---------------------------------------------------------------------------
# bm25 edge cases
# ---------------------------------------------------------------------------


def test_bm25_exception_returns_chunks():
    from app.services import bm25_service as b

    with patch("rank_bm25.BM25Okapi", side_effect=RuntimeError("bm25 fail")):
        chunks = [{"chunk_id": "c1", "chunk_text": "hello world"}]
        assert b.compute_bm25_scores("hello", chunks) == chunks


def test_bm25_comparison_empty_chunks():
    from app.services.bm25_service import get_bm25_comparison

    result = get_bm25_comparison("q", [])
    assert result["comparable"] is False
    assert result["chunks_with_bm25"] == []


# ---------------------------------------------------------------------------
# context_recall deeper paths
# ---------------------------------------------------------------------------


def test_context_recall_no_significant_tokens_uses_similarity_fallback():
    from app.services.context_recall import compute_context_recall_heuristic

    # Query of only stopwords → _max_query_chunk_similarity with model=None → 0.5
    score = compute_context_recall_heuristic("the a an", ["some chunk text here"])
    assert score == 0.5


def test_context_recall_answer_attribution_lexical():
    from app.services.context_recall import compute_context_recall_heuristic

    score = compute_context_recall_heuristic(
        "OAuth refresh tokens",
        ["OAuth refresh tokens are used to renew access tokens safely."],
        answer="OAuth refresh tokens renew access. Extra filler sentence here.",
    )
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_context_recall_llm_and_prefer_paths():
    from app.services.context_recall import compute_context_recall, compute_context_recall_llm

    assert await compute_context_recall_llm("", [], "u", "m") == 0.0

    async def fake_gen(prompt, *args, **kwargs):
        if "JSON array" in prompt:
            return '["need one", "need two"]'
        return "yes"

    with patch("app.services.ragas_service.llm_generate", side_effect=fake_gen):
        score = await compute_context_recall_llm(
            "What is OAuth?",
            ["OAuth is an auth protocol."],
            "http://ollama",
            "llama",
        )
    assert score == 1.0

    with patch(
        "app.services.context_recall.compute_context_recall_llm",
        new=AsyncMock(return_value=0.75),
    ):
        out = await compute_context_recall(
            "What is OAuth refresh?",
            ["OAuth refresh tokens document."],
            ollama_url="http://o",
            model="m",
            prefer_llm=True,
        )
    assert out == 0.75

    with patch(
        "app.services.context_recall.compute_context_recall_llm",
        new=AsyncMock(side_effect=RuntimeError("llm down")),
    ):
        out = await compute_context_recall(
            "What is OAuth refresh tokens about?",
            ["OAuth refresh tokens are documented here."],
            ollama_url="http://o",
            model="m",
            prefer_llm=True,
        )
    assert isinstance(out, float)


@pytest.mark.asyncio
async def test_context_recall_llm_parses_non_json_needs():
    from app.services.context_recall import compute_context_recall_llm

    async def fake_gen(prompt, *args, **kwargs):
        if "JSON array" in prompt:
            # Valid brackets but invalid JSON → except path line-parses needs
            return "[not valid json]\n- oauth token refresh mechanics need"
        return "yes"

    with patch("app.services.ragas_service.llm_generate", side_effect=fake_gen):
        score = await compute_context_recall_llm(
            "What is OAuth?",
            ["context"],
            "http://o",
            "m",
        )
    assert score == 1.0


def test_max_query_chunk_similarity_with_fake_model():
    from app.services.context_recall import _max_query_chunk_similarity

    class Vec(list):
        def tolist(self):
            return list(self)

    class FakeEmb:
        def encode(self, text):
            return Vec([1.0, 0.0])

    with patch("app.services.ragas_service.get_embedding_model", return_value=FakeEmb()):
        with patch("app.services.ragas_service.cosine_similarity", return_value=0.8):
            assert _max_query_chunk_similarity("query", ["chunk"]) == 0.8


def test_answer_attribution_with_embeddings():
    from app.services.context_recall import _answer_attribution_coverage

    class Vec(list):
        def tolist(self):
            return list(self)

    class FakeEmb:
        def encode(self, text):
            return Vec([1.0, 0.0])

    with patch("app.services.ragas_service.get_embedding_model", return_value=FakeEmb()):
        with patch("app.services.ragas_service.cosine_similarity", return_value=0.9):
            cov = _answer_attribution_coverage(
                ["This is a long enough answer sentence."],
                ["chunk text"],
                0.35,
            )
    assert cov == 1.0


def test_max_query_chunk_similarity_exception_fallback():
    from app.services.context_recall import _max_query_chunk_similarity

    class BoomEmb:
        def encode(self, text):
            raise RuntimeError("encode fail")

    with patch("app.services.ragas_service.get_embedding_model", return_value=BoomEmb()):
        assert _max_query_chunk_similarity("query", ["chunk"]) == 0.5


def test_answer_attribution_exception_lexical_fallback():
    from app.services.context_recall import _answer_attribution_coverage

    class BoomEmb:
        def encode(self, text):
            raise RuntimeError("encode fail")

    with patch("app.services.ragas_service.get_embedding_model", return_value=BoomEmb()):
        cov = _answer_attribution_coverage(
            ["OAuth refresh token sentence here."],
            ["OAuth refresh token corpus text."],
            0.35,
        )
    assert 0.0 <= cov <= 1.0


# ---------------------------------------------------------------------------
# slack alerts
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_slack_alert_async_paths():
    from app.services.slack_alerts import send_daily_summary_alert, send_slack_alert

    assert await send_slack_alert("bad-url", "msg") is False

    mock_resp = MagicMock(status_code=200)
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = False
    mock_client.post = AsyncMock(return_value=mock_resp)

    with patch("app.services.slack_alerts.httpx.AsyncClient", return_value=mock_client):
        ok = await send_slack_alert("https://hooks.slack.com/services/T/B/X", "hello")
    assert ok is True

    mock_resp.status_code = 500
    mock_resp.text = "fail"
    with patch("app.services.slack_alerts.httpx.AsyncClient", return_value=mock_client):
        assert await send_slack_alert("https://hooks.slack.com/services/T/B/X", "hello") is False

    mock_client.post = AsyncMock(side_effect=RuntimeError("net"))
    with patch("app.services.slack_alerts.httpx.AsyncClient", return_value=mock_client):
        assert await send_slack_alert("https://hooks.slack.com/services/T/B/X", "hello") is False

    mock_client.post = AsyncMock(return_value=MagicMock(status_code=200))
    with patch("app.services.slack_alerts.httpx.AsyncClient", return_value=mock_client):
        assert await send_daily_summary_alert(
            "https://hooks.slack.com/services/T/B/X",
            "Ada",
            85.0,
            10,
            1,
            "hallucination",
            "http://app/dashboard",
        )


def test_slack_alert_sync_and_hallucination():
    from app.services.slack_alerts import send_hallucination_alert_sync, send_slack_alert_sync

    assert send_slack_alert_sync("nope", "m") is False

    mock_resp = MagicMock(status_code=200)
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = MagicMock(post=MagicMock(return_value=mock_resp))
    mock_cm.__exit__.return_value = False
    with patch("app.services.slack_alerts.httpx.Client", return_value=mock_cm):
        assert send_slack_alert_sync("https://hooks.slack.com/services/T/B/X", "m") is True
        assert send_hallucination_alert_sync(
            "https://hooks.slack.com/services/T/B/X",
            "pipe",
            "query text",
            0.2,
            "http://dash",
        )

    mock_cm.__enter__.return_value.post.side_effect = RuntimeError("down")
    with patch("app.services.slack_alerts.httpx.Client", return_value=mock_cm):
        assert send_slack_alert_sync("https://hooks.slack.com/services/T/B/X", "m") is False


# ---------------------------------------------------------------------------
# worker maintenance tasks
# ---------------------------------------------------------------------------


def _sync_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine), engine


def test_database_task_get_sync_session():
    from app.workers.tasks import DatabaseTask

    task = DatabaseTask()
    with patch("app.db.session.sync_engine", create_engine("sqlite://")):
        session = task.get_sync_session()
        assert isinstance(session, Session)
        session.close()


def test_reset_monthly_traces():
    from app.workers.tasks import reset_monthly_traces

    SessionLocal, engine = _sync_session()
    with SessionLocal() as db:
        user = User(
            id=str(uuid.uuid4()),
            email="reset@example.com",
            password_hash="h",
            name="R",
            traces_this_month=42,
        )
        db.add(user)
        db.commit()

    with patch("app.db.session.sync_engine", engine):
        reset_monthly_traces()

    with SessionLocal() as db:
        u = db.query(User).one()
        assert u.traces_this_month == 0


def test_update_chunk_citation_rates():
    from app.workers.tasks import update_chunk_citation_rates

    SessionLocal, engine = _sync_session()
    with SessionLocal() as db:
        user = User(
            id=str(uuid.uuid4()),
            email="cite@example.com",
            password_hash="h",
            name="C",
        )
        db.add(user)
        db.flush()
        pipe = Pipeline(id=str(uuid.uuid4()), user_id=user.id, name="p")
        db.add(pipe)
        db.flush()
        db.add(
            ChunkStat(
                id=str(uuid.uuid4()),
                chunk_id="c1",
                pipeline_id=pipe.id,
                text="chunk",
                retrieval_count=60,
                citation_count=5,
                citation_rate=0.0,
                is_flagged=False,
            )
        )
        db.commit()

    with patch("app.db.session.sync_engine", engine):
        update_chunk_citation_rates()

    with SessionLocal() as db:
        chunk = db.query(ChunkStat).one()
        assert chunk.is_flagged is True
        assert chunk.citation_rate < 0.2


def test_deliver_webhook_success_and_skip():
    from app.workers.tasks import deliver_webhook

    SessionLocal, engine = _sync_session()
    with SessionLocal() as db:
        user = User(
            id=str(uuid.uuid4()),
            email="hook@example.com",
            password_hash="h",
            name="H",
        )
        db.add(user)
        db.flush()
        webhook = IntegrationWebhook(
            id=str(uuid.uuid4()),
            user_id=user.id,
            provider="slack",
            name="wh",
            webhook_url="https://example.com/hook",
            is_active=True,
            events='["trace.analyzed"]',
        )
        db.add(webhook)
        db.flush()
        delivery = WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_id=webhook.id,
            event_type="trace.analyzed",
            payload_json='{"ok": true}',
            status="pending",
            attempts=0,
        )
        db.add(delivery)
        inactive = IntegrationWebhook(
            id=str(uuid.uuid4()),
            user_id=user.id,
            provider="generic",
            name="off",
            webhook_url="https://example.com/off",
            is_active=False,
            events="[]",
        )
        db.add(inactive)
        db.flush()
        skipped = WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_id=inactive.id,
            event_type="trace.analyzed",
            payload_json="{}",
            status="pending",
            attempts=0,
        )
        db.add(skipped)
        db.commit()
        delivery_id = delivery.id
        skipped_id = skipped.id

    mock_resp = MagicMock(status_code=200)
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = MagicMock(post=MagicMock(return_value=mock_resp))
    mock_cm.__exit__.return_value = False

    with patch("app.db.session.sync_engine", engine), patch(
        "httpx.Client", return_value=mock_cm
    ):
        deliver_webhook.run(delivery_id)

    with SessionLocal() as db:
        d = db.get(WebhookDelivery, delivery_id)
        assert d.status == "delivered"

    with patch("app.db.session.sync_engine", engine):
        deliver_webhook.run(skipped_id)
        deliver_webhook.run("missing-id")

    with SessionLocal() as db:
        s = db.get(WebhookDelivery, skipped_id)
        assert s.status == "skipped"


def test_deliver_webhook_retries_on_http_error():
    from app.workers.tasks import deliver_webhook

    SessionLocal, engine = _sync_session()
    with SessionLocal() as db:
        user = User(
            id=str(uuid.uuid4()),
            email="hook2@example.com",
            password_hash="h",
            name="H2",
        )
        db.add(user)
        db.flush()
        webhook = IntegrationWebhook(
            id=str(uuid.uuid4()),
            user_id=user.id,
            provider="generic",
            name="wh2",
            webhook_url="https://example.com/hook",
            is_active=True,
            events="[]",
        )
        db.add(webhook)
        db.flush()
        delivery = WebhookDelivery(
            id=str(uuid.uuid4()),
            webhook_id=webhook.id,
            event_type="trace.analyzed",
            payload_json="{}",
            status="pending",
            attempts=0,
        )
        db.add(delivery)
        db.commit()
        delivery_id = delivery.id

    mock_resp = MagicMock(status_code=500)
    mock_cm = MagicMock()
    mock_cm.__enter__.return_value = MagicMock(post=MagicMock(return_value=mock_resp))
    mock_cm.__exit__.return_value = False

    with patch("app.db.session.sync_engine", engine), patch(
        "httpx.Client", return_value=mock_cm
    ):
        with pytest.raises(Exception):
            deliver_webhook.run(delivery_id)


def test_send_weekly_executive_reports():
    from app.workers.tasks import send_weekly_executive_reports

    SessionLocal, engine = _sync_session()
    with SessionLocal() as db:
        user = User(
            id=str(uuid.uuid4()),
            email="exec@example.com",
            password_hash="h",
            name="E",
        )
        db.add(user)
        db.flush()
        db.add(
            WeeklyExecutiveReport(
                id=str(uuid.uuid4()),
                user_id=user.id,
                recipient_email="exec@example.com",
                enabled=True,
            )
        )
        db.commit()

    with patch("app.db.session.sync_engine", engine):
        send_weekly_executive_reports()
