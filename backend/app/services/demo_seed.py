"""Demo dataset for local UX without a real RAG app (Phase 7.3).

Idempotent: re-running updates the demo user password/settings and refreshes
sample traces when ``force=True``; otherwise skips if demo user already exists
with a pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import NAMESPACE_DNS, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_password_hash
from app.models.models import (
    AnalysisJob,
    ChunkStat,
    FailureType,
    FixRecommendation,
    GroundingResult,
    JobStatus,
    Pipeline,
    QueryTrace,
    RetrievedChunk,
    SubscriptionPlan,
    User,
    UserRole,
    UserSettings,
)

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "DemoPass123!"
DEMO_NAME = "Demo User"

# Stable IDs so re-seeds stay predictable across DBs
_NS = uuid5(NAMESPACE_DNS, "raginspector.demo")
DEMO_USER_ID = str(uuid5(_NS, "user"))
DEMO_PIPELINE_ID = str(uuid5(_NS, "pipeline"))
DEMO_SETTINGS_ID = str(uuid5(_NS, "settings"))


def _tid(key: str) -> str:
    return str(uuid5(_NS, f"trace:{key}"))


def _cid(key: str) -> str:
    return str(uuid5(_NS, f"chunkstat:{key}"))


@dataclass
class SeedResult:
    created: bool
    user_id: str
    pipeline_id: str
    email: str
    password: str
    trace_count: int
    message: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _sample_specs() -> list[dict[str, Any]]:
    """Pre-scored traces — no Celery/ML required for dashboard/query detail."""
    base = _now()
    return [
        {
            "key": "grounded",
            "traced_at": base - timedelta(hours=2),
            "query_text": "What is the refund window for annual plans?",
            "answer_text": (
                "Annual plans can be refunded within 14 days of purchase. "
                "After that window, upgrades are prorated only."
            ),
            "faithfulness_score": 0.94,
            "answer_relevance_score": 0.91,
            "context_precision_score": 0.88,
            "context_recall_score": 0.85,
            "grounded_fraction": 1.0,
            "trustworthiness_score": 0.91,
            "is_hallucination": False,
            "failure_type": FailureType.none,
            "failure_explanation": None,
            "recommendation": None,
            "embed_latency_ms": 12.0,
            "retrieve_latency_ms": 45.0,
            "generate_latency_ms": 320.0,
            "chunks": [
                {
                    "chunk_id": "doc-billing-01",
                    "chunk_text": (
                        "Annual subscriptions may be refunded in full within 14 days "
                        "of the original purchase date. After 14 days, only prorated "
                        "plan upgrades are available."
                    ),
                    "similarity_score": 0.91,
                    "bm25_score": 8.2,
                    "was_cited": True,
                },
                {
                    "chunk_id": "doc-billing-02",
                    "chunk_text": "Monthly plans renew automatically unless cancelled.",
                    "similarity_score": 0.55,
                    "bm25_score": 2.1,
                    "was_cited": False,
                },
            ],
            "sentences": [
                {
                    "text": "Annual plans can be refunded within 14 days of purchase.",
                    "grounded": True,
                    "chunk_id": "doc-billing-01",
                    "confidence": 0.93,
                },
                {
                    "text": "After that window, upgrades are prorated only.",
                    "grounded": True,
                    "chunk_id": "doc-billing-01",
                    "confidence": 0.89,
                },
            ],
        },
        {
            "key": "hallucination",
            "traced_at": base - timedelta(hours=5),
            "query_text": "Does the API support streaming responses?",
            "answer_text": (
                "Yes. The API supports SSE streaming on /v1/chat/completions "
                "and guarantees exactly-once delivery."
            ),
            "faithfulness_score": 0.32,
            "answer_relevance_score": 0.7,
            "context_precision_score": 0.4,
            "context_recall_score": 0.35,
            "grounded_fraction": 0.33,
            "trustworthiness_score": 0.38,
            "is_hallucination": True,
            "failure_type": FailureType.hallucination,
            "failure_explanation": "Answer invents exactly-once delivery not present in context.",
            "recommendation": "Tighten generation prompt; cite only retrieved chunks.",
            "embed_latency_ms": 11.0,
            "retrieve_latency_ms": 52.0,
            "generate_latency_ms": 410.0,
            "chunks": [
                {
                    "chunk_id": "doc-api-01",
                    "chunk_text": (
                        "The chat completions endpoint returns a single JSON response. "
                        "Streaming is on the roadmap and not yet available."
                    ),
                    "similarity_score": 0.82,
                    "bm25_score": 7.0,
                    "was_cited": True,
                },
            ],
            "sentences": [
                {
                    "text": "Yes. The API supports SSE streaming on /v1/chat/completions",
                    "grounded": False,
                    "chunk_id": None,
                    "confidence": 0.22,
                },
                {
                    "text": "and guarantees exactly-once delivery.",
                    "grounded": False,
                    "chunk_id": None,
                    "confidence": 0.15,
                },
            ],
        },
        {
            "key": "retrieval_miss",
            "traced_at": base - timedelta(days=1, hours=3),
            "query_text": "How do I rotate API keys?",
            "answer_text": "I could not find key rotation steps in the knowledge base.",
            "faithfulness_score": 0.8,
            "answer_relevance_score": 0.45,
            "context_precision_score": 0.2,
            "context_recall_score": 0.1,
            "grounded_fraction": 0.9,
            "trustworthiness_score": 0.55,
            "is_hallucination": False,
            "failure_type": FailureType.retrieval_miss,
            "failure_explanation": "Top chunks are unrelated to API key rotation.",
            "recommendation": "Add a keys/rotation doc chunk; improve embedding coverage.",
            "embed_latency_ms": 10.0,
            "retrieve_latency_ms": 60.0,
            "generate_latency_ms": 280.0,
            "chunks": [
                {
                    "chunk_id": "doc-onboarding-01",
                    "chunk_text": "Welcome to RAGInspector. Create your first pipeline from Settings.",
                    "similarity_score": 0.41,
                    "bm25_score": 1.2,
                    "was_cited": False,
                },
            ],
            "sentences": [
                {
                    "text": "I could not find key rotation steps in the knowledge base.",
                    "grounded": True,
                    "chunk_id": "doc-onboarding-01",
                    "confidence": 0.6,
                },
            ],
        },
        {
            "key": "coverage_gap",
            "traced_at": base - timedelta(days=2),
            "query_text": "What SLA do enterprise customers get?",
            "answer_text": (
                "Enterprise customers receive 99.9% uptime. "
                "Dedicated support is available during business hours."
            ),
            "faithfulness_score": 0.55,
            "answer_relevance_score": 0.75,
            "context_precision_score": 0.5,
            "context_recall_score": 0.3,
            "grounded_fraction": 0.5,
            "trustworthiness_score": 0.52,
            "is_hallucination": False,
            "failure_type": FailureType.coverage_gap,
            "failure_explanation": "SLA percentage not in retrieved corpus; only support hours found.",
            "recommendation": "Ingest enterprise SLA PDF into the vector index.",
            "embed_latency_ms": 13.0,
            "retrieve_latency_ms": 48.0,
            "generate_latency_ms": 350.0,
            "chunks": [
                {
                    "chunk_id": "doc-support-01",
                    "chunk_text": (
                        "Enterprise plans include dedicated email support during "
                        "business hours (09:00–18:00 UTC)."
                    ),
                    "similarity_score": 0.78,
                    "bm25_score": 6.5,
                    "was_cited": True,
                },
            ],
            "sentences": [
                {
                    "text": "Enterprise customers receive 99.9% uptime.",
                    "grounded": False,
                    "chunk_id": None,
                    "confidence": 0.2,
                },
                {
                    "text": "Dedicated support is available during business hours.",
                    "grounded": True,
                    "chunk_id": "doc-support-01",
                    "confidence": 0.9,
                },
            ],
        },
    ]


def _purge_demo_pipeline_children(session: Session, pipeline_id: str) -> None:
    traces = session.scalars(select(QueryTrace).where(QueryTrace.pipeline_id == pipeline_id)).all()
    for t in traces:
        session.delete(t)
    for cs in session.scalars(select(ChunkStat).where(ChunkStat.pipeline_id == pipeline_id)).all():
        session.delete(cs)


def seed_demo_data(session: Session, *, force: bool = False) -> SeedResult:
    """Insert or refresh demo user + pipeline + analyzed sample traces."""
    existing = session.scalar(select(User).where(User.email == DEMO_EMAIL))
    if existing and not force:
        pipes = session.scalars(select(Pipeline).where(Pipeline.user_id == existing.id)).all()
        if pipes:
            trace_n = session.scalar(
                select(QueryTrace.id).where(QueryTrace.pipeline_id == pipes[0].id).limit(1)
            )
            if trace_n:
                return SeedResult(
                    created=False,
                    user_id=str(existing.id),
                    pipeline_id=str(pipes[0].id),
                    email=DEMO_EMAIL,
                    password=DEMO_PASSWORD,
                    trace_count=0,
                    message="Demo already present (pass --force to refresh).",
                )

    if existing and force:
        for p in session.scalars(select(Pipeline).where(Pipeline.user_id == existing.id)).all():
            _purge_demo_pipeline_children(session, str(p.id))
            session.delete(p)
        for fr in session.scalars(
            select(FixRecommendation).where(FixRecommendation.user_id == existing.id)
        ).all():
            session.delete(fr)
        user = existing
        user.password_hash = get_password_hash(DEMO_PASSWORD)
        user.name = DEMO_NAME
        user.email_verified = True
        user.onboarding_completed = True
        user.is_active = True
        user.subscription_plan = SubscriptionPlan.starter
        user.traces_this_month = 4
    elif existing:
        user = existing
        user.password_hash = get_password_hash(DEMO_PASSWORD)
        user.email_verified = True
        user.onboarding_completed = True
    else:
        user = User(
            id=DEMO_USER_ID,
            email=DEMO_EMAIL,
            password_hash=get_password_hash(DEMO_PASSWORD),
            name=DEMO_NAME,
            role=UserRole.owner,
            is_active=True,
            subscription_plan=SubscriptionPlan.starter,
            email_verified=True,
            onboarding_completed=True,
            traces_this_month=4,
        )
        session.add(user)
        session.flush()

    settings = session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    if not settings:
        session.add(
            UserSettings(
                id=DEMO_SETTINGS_ID,
                user_id=user.id,
            )
        )

    pipeline = session.scalar(select(Pipeline).where(Pipeline.id == DEMO_PIPELINE_ID))
    if not pipeline:
        pipeline = session.scalar(
            select(Pipeline).where(
                Pipeline.user_id == user.id,
                Pipeline.name == "Demo RAG Pipeline",
            )
        )
    if not pipeline:
        pipeline = Pipeline(
            id=DEMO_PIPELINE_ID,
            user_id=user.id,
            name="Demo RAG Pipeline",
            description="Seeded sample pipeline for local demos (no live RAG app required).",
            queries_per_month=10_000,
            cost_per_wrong_answer_usd=5.0,
        )
        session.add(pipeline)
        session.flush()
    else:
        pipeline.name = "Demo RAG Pipeline"
        pipeline.description = "Seeded sample pipeline for local demos (no live RAG app required)."

    if force:
        _purge_demo_pipeline_children(session, str(pipeline.id))

    existing_traces = session.scalars(
        select(QueryTrace).where(QueryTrace.pipeline_id == pipeline.id)
    ).all()
    if existing_traces and not force:
        session.commit()
        return SeedResult(
            created=False,
            user_id=str(user.id),
            pipeline_id=str(pipeline.id),
            email=DEMO_EMAIL,
            password=DEMO_PASSWORD,
            trace_count=len(existing_traces),
            message="Demo user/pipeline ready; traces already exist.",
        )

    chunk_stats: dict[str, ChunkStat] = {}
    for spec in _sample_specs():
        trace_id = _tid(spec["key"])
        trace = QueryTrace(
            id=trace_id,
            pipeline_id=pipeline.id,
            query_text=spec["query_text"],
            answer_text=spec["answer_text"],
            faithfulness_score=spec["faithfulness_score"],
            answer_relevance_score=spec["answer_relevance_score"],
            context_precision_score=spec["context_precision_score"],
            context_recall_score=spec["context_recall_score"],
            grounded_fraction=spec["grounded_fraction"],
            trustworthiness_score=spec["trustworthiness_score"],
            is_hallucination=spec["is_hallucination"],
            failure_type=spec["failure_type"],
            failure_explanation=spec["failure_explanation"],
            recommendation=spec["recommendation"],
            embed_latency_ms=spec["embed_latency_ms"],
            retrieve_latency_ms=spec["retrieve_latency_ms"],
            generate_latency_ms=spec["generate_latency_ms"],
            analysis_status="completed",
            traced_at=spec["traced_at"],
        )
        session.add(trace)
        session.flush()

        for i, ch in enumerate(spec["chunks"]):
            session.add(
                RetrievedChunk(
                    id=str(uuid5(_NS, f"rc:{spec['key']}:{ch['chunk_id']}")),
                    trace_id=trace.id,
                    chunk_id=ch["chunk_id"],
                    chunk_text=ch["chunk_text"],
                    similarity_score=ch["similarity_score"],
                    bm25_score=ch.get("bm25_score"),
                    rank=i + 1,
                    was_cited=bool(ch.get("was_cited")),
                )
            )
            cid = ch["chunk_id"]
            if cid not in chunk_stats:
                cs = ChunkStat(
                    id=_cid(cid),
                    chunk_id=cid,
                    pipeline_id=pipeline.id,
                    text=ch["chunk_text"],
                    retrieval_count=0,
                    citation_count=0,
                    citation_rate=0.0,
                    is_flagged=False,
                )
                session.add(cs)
                chunk_stats[cid] = cs
            chunk_stats[cid].retrieval_count = int(chunk_stats[cid].retrieval_count or 0) + 1
            if ch.get("was_cited"):
                chunk_stats[cid].citation_count = int(chunk_stats[cid].citation_count or 0) + 1

        for i, sent in enumerate(spec["sentences"]):
            session.add(
                GroundingResult(
                    id=str(uuid5(_NS, f"gr:{spec['key']}:{i}")),
                    trace_id=trace.id,
                    sentence_text=sent["text"],
                    sentence_index=i,
                    is_grounded=bool(sent["grounded"]),
                    supporting_chunk_id=sent.get("chunk_id"),
                    confidence_score=sent.get("confidence"),
                )
            )

        session.add(
            AnalysisJob(
                id=str(uuid5(_NS, f"job:{spec['key']}")),
                trace_id=trace.id,
                status=JobStatus.completed,
                started_at=spec["traced_at"],
                completed_at=spec["traced_at"] + timedelta(seconds=8),
            )
        )

    for cs in chunk_stats.values():
        rc = int(cs.retrieval_count or 0)
        cc = int(cs.citation_count or 0)
        cs.citation_rate = (cc / rc) if rc else 0.0
        # Flag a low-citation frequently retrieved chunk for heatmap demos
        if cs.chunk_id == "doc-onboarding-01":
            cs.retrieval_count = 55
            cs.citation_count = 2
            cs.citation_rate = 2 / 55
            cs.is_flagged = True

    rec = session.scalar(
        select(FixRecommendation).where(
            FixRecommendation.user_id == user.id,
            FixRecommendation.topic_description == "Add API key rotation documentation",
        )
    )
    if not rec:
        session.add(
            FixRecommendation(
                id=str(uuid5(_NS, "fixrec:keys")),
                user_id=user.id,
                recommendation_type="coverage_gap",
                topic_description="Add API key rotation documentation",
                affected_query_count=1,
                sample_queries='["How do I rotate API keys?"]',
            )
        )

    session.commit()
    return SeedResult(
        created=True,
        user_id=str(user.id),
        pipeline_id=str(pipeline.id),
        email=DEMO_EMAIL,
        password=DEMO_PASSWORD,
        trace_count=len(_sample_specs()),
        message="Demo dataset seeded.",
    )
