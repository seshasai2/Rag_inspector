"""Demo dataset for local UX without a real RAG app (Phase 7.3 + Phase 10).

Idempotent: re-running updates the demo user password/settings and refreshes
sample traces when ``force=True``; otherwise skips existing rows and backfills
any missing Phase 10 demo assets (gaps, documents, monitoring, regression,
reports, org, API key).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import NAMESPACE_DNS, uuid5

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import get_key_prefix, get_password_hash, hash_api_key
from app.models.models import (
    APIKey,
    AnalysisJob,
    ChunkStat,
    Document,
    FailureType,
    FixRecommendation,
    GroundingResult,
    JobStatus,
    KnowledgeGap,
    MonitoringConfig,
    MonitoringRun,
    Organization,
    OrganizationMember,
    Pipeline,
    QueryTrace,
    RegressionSnapshot,
    ReportHistory,
    RetrievedChunk,
    SLAThreshold,
    SubscriptionPlan,
    User,
    UserRole,
    UserSettings,
    WeeklyExecutiveReport,
)

DEMO_EMAIL = "demo@example.com"
DEMO_PASSWORD = "DemoPass123!"
DEMO_NAME = "Demo User"
# Deterministic local-only key — never use outside demo/seed environments.
DEMO_API_KEY = "ri-demo_interview_seed_key_000000000001"
DEMO_ORG_NAME = "Acme Support Labs"
DEMO_ORG_SLUG = "acme-support-labs"

# Stable IDs so re-seeds stay predictable across DBs
_NS = uuid5(NAMESPACE_DNS, "raginspector.demo")
DEMO_USER_ID = str(uuid5(_NS, "user"))
DEMO_ORG_ID = str(uuid5(_NS, "org"))
DEMO_MEMBER_ID = str(uuid5(_NS, "org-member"))
DEMO_PIPELINE_ID = str(uuid5(_NS, "pipeline"))
DEMO_PIPELINE_B_ID = str(uuid5(_NS, "pipeline-b"))
DEMO_SETTINGS_ID = str(uuid5(_NS, "settings"))
DEMO_API_KEY_ID = str(uuid5(_NS, "api-key"))


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
    api_key: str
    organization_id: str
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
    for gap in session.scalars(select(KnowledgeGap).where(KnowledgeGap.pipeline_id == pipeline_id)).all():
        session.delete(gap)
    for doc in session.scalars(select(Document).where(Document.pipeline_id == pipeline_id)).all():
        session.delete(doc)
    for run in session.scalars(select(MonitoringRun).where(MonitoringRun.pipeline_id == pipeline_id)).all():
        session.delete(run)
    for cfg in session.scalars(
        select(MonitoringConfig).where(MonitoringConfig.pipeline_id == pipeline_id)
    ).all():
        session.delete(cfg)
    for snap in session.scalars(
        select(RegressionSnapshot).where(RegressionSnapshot.pipeline_id == pipeline_id)
    ).all():
        session.delete(snap)


def _ensure_org(session: Session, user: User) -> Organization:
    org = session.scalar(select(Organization).where(Organization.id == DEMO_ORG_ID))
    if not org:
        org = session.scalar(select(Organization).where(Organization.slug == DEMO_ORG_SLUG))
    if not org:
        org = Organization(
            id=DEMO_ORG_ID,
            name=DEMO_ORG_NAME,
            slug=DEMO_ORG_SLUG,
            allowed_domains="example.com",
            sso_required=False,
            mfa_required=False,
        )
        session.add(org)
        session.flush()
    else:
        org.name = DEMO_ORG_NAME
        org.slug = DEMO_ORG_SLUG

    user.organization_id = org.id
    member = session.scalar(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org.id,
            OrganizationMember.user_id == user.id,
        )
    )
    if not member:
        session.add(
            OrganizationMember(
                id=DEMO_MEMBER_ID,
                organization_id=org.id,
                user_id=user.id,
                role=UserRole.owner,
                invited_email=DEMO_EMAIL,
                accepted_at=_now(),
            )
        )
    return org


def _ensure_api_key(session: Session, user: User, org: Organization) -> str:
    existing = session.scalar(select(APIKey).where(APIKey.id == DEMO_API_KEY_ID))
    hashed = hash_api_key(DEMO_API_KEY)
    prefix = get_key_prefix(DEMO_API_KEY)
    if existing:
        existing.key_hash = hashed
        existing.key_prefix = prefix
        existing.name = "Demo Interview SDK Key"
        existing.is_active = True
        existing.user_id = user.id
        existing.organization_id = org.id
        existing.scopes = json.dumps(["ingest:write", "metrics:read"])
        return DEMO_API_KEY

    # Avoid unique conflicts if a prior seed used a different id for the same hash
    by_hash = session.scalar(select(APIKey).where(APIKey.key_hash == hashed))
    if by_hash:
        by_hash.name = "Demo Interview SDK Key"
        by_hash.is_active = True
        by_hash.key_prefix = prefix
        by_hash.user_id = user.id
        by_hash.organization_id = org.id
        by_hash.scopes = json.dumps(["ingest:write", "metrics:read"])
        return DEMO_API_KEY

    session.add(
        APIKey(
            id=DEMO_API_KEY_ID,
            user_id=user.id,
            organization_id=org.id,
            key_hash=hashed,
            key_prefix=prefix,
            name="Demo Interview SDK Key",
            scopes=json.dumps(["ingest:write", "metrics:read"]),
            is_active=True,
        )
    )
    return DEMO_API_KEY


def _ensure_pipelines(session: Session, user: User, org: Organization) -> tuple[Pipeline, Pipeline]:
    primary = session.scalar(select(Pipeline).where(Pipeline.id == DEMO_PIPELINE_ID))
    if not primary:
        primary = session.scalar(
            select(Pipeline).where(
                Pipeline.user_id == user.id,
                Pipeline.name == "Demo RAG Pipeline",
            )
        )
    if not primary:
        primary = Pipeline(
            id=DEMO_PIPELINE_ID,
            user_id=user.id,
            organization_id=org.id,
            name="Demo RAG Pipeline",
            description="Seeded sample pipeline for local demos (no live RAG app required).",
            queries_per_month=10_000,
            cost_per_wrong_answer_usd=5.0,
        )
        session.add(primary)
        session.flush()
    else:
        primary.name = "Demo RAG Pipeline"
        primary.description = "Seeded sample pipeline for local demos (no live RAG app required)."
        primary.organization_id = org.id
        primary.queries_per_month = 10_000
        primary.cost_per_wrong_answer_usd = 5.0

    secondary = session.scalar(select(Pipeline).where(Pipeline.id == DEMO_PIPELINE_B_ID))
    if not secondary:
        secondary = session.scalar(
            select(Pipeline).where(
                Pipeline.user_id == user.id,
                Pipeline.name == "Docs Assistant",
            )
        )
    if not secondary:
        secondary = Pipeline(
            id=DEMO_PIPELINE_B_ID,
            user_id=user.id,
            organization_id=org.id,
            name="Docs Assistant",
            description="Secondary pipeline for compare / multi-pipeline demos.",
            queries_per_month=5_000,
            cost_per_wrong_answer_usd=3.0,
        )
        session.add(secondary)
        session.flush()
    else:
        secondary.name = "Docs Assistant"
        secondary.organization_id = org.id

    return primary, secondary


def _seed_traces(session: Session, pipeline: Pipeline) -> int:
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
        if cs.chunk_id == "doc-onboarding-01":
            cs.retrieval_count = 55
            cs.citation_count = 2
            cs.citation_rate = 2 / 55
            cs.is_flagged = True

    return len(_sample_specs())


def _ensure_fix_recommendation(session: Session, user: User, pipeline: Pipeline) -> None:
    rec = session.scalar(
        select(FixRecommendation).where(FixRecommendation.id == str(uuid5(_NS, "fixrec:keys")))
    )
    if not rec:
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
                pipeline_id=pipeline.id,
                recommendation_type="coverage_gap",
                topic_description="Add API key rotation documentation",
                affected_query_count=3,
                sample_queries='["How do I rotate API keys?","Where is key rotation documented?"]',
                status="open",
                trust_score_before=0.55,
            )
        )
        session.add(
            FixRecommendation(
                id=str(uuid5(_NS, "fixrec:streaming")),
                user_id=user.id,
                pipeline_id=pipeline.id,
                recommendation_type="hybrid_search",
                topic_description="Clarify streaming API status in generation prompt",
                affected_query_count=2,
                sample_queries='["Does the API support streaming responses?"]',
                status="open",
                trust_score_before=0.38,
            )
        )


def _ensure_phase10_assets(
    session: Session, user: User, org: Organization, pipeline: Pipeline
) -> None:
    """Knowledge gaps, documents, monitoring, regression, SLA, reports."""
    now = _now()

    gap_specs = [
        {
            "id": str(uuid5(_NS, "gap:keys")),
            "topic_label": "API key rotation",
            "representative_query": "How do I rotate API keys?",
            "query_count": 12,
            "failure_rate": 0.67,
            "affected_users_estimate": 40,
            "estimated_monthly_cost_usd": 180.0,
            "priority": "high",
            "suggested_document_topic": "Security → API key lifecycle",
            "auto_fix_draft": (
                "# API key rotation\n\n1. Open Settings → API keys.\n"
                "2. Click Rotate on the active key.\n"
                "3. Update SDK clients within 24 hours.\n"
            ),
            "status": "open",
        },
        {
            "id": str(uuid5(_NS, "gap:sla")),
            "topic_label": "Enterprise SLA uptime",
            "representative_query": "What SLA do enterprise customers get?",
            "query_count": 8,
            "failure_rate": 0.5,
            "affected_users_estimate": 15,
            "estimated_monthly_cost_usd": 95.0,
            "priority": "medium",
            "suggested_document_topic": "Enterprise → SLA & support hours",
            "auto_fix_draft": (
                "# Enterprise SLA\n\nEnterprise plans include 99.9% monthly uptime "
                "and dedicated support 09:00–18:00 UTC.\n"
            ),
            "status": "open",
        },
    ]
    for g in gap_specs:
        existing = session.scalar(select(KnowledgeGap).where(KnowledgeGap.id == g["id"]))
        if existing:
            continue
        session.add(
            KnowledgeGap(
                id=g["id"],
                pipeline_id=pipeline.id,
                topic_label=g["topic_label"],
                representative_query=g["representative_query"],
                query_count=g["query_count"],
                failure_rate=g["failure_rate"],
                affected_users_estimate=g["affected_users_estimate"],
                estimated_monthly_cost_usd=g["estimated_monthly_cost_usd"],
                priority=g["priority"],
                suggested_document_topic=g["suggested_document_topic"],
                auto_fix_draft=g["auto_fix_draft"],
                fix_format="markdown",
                status=g["status"],
            )
        )

    doc_specs = [
        {
            "id": str(uuid5(_NS, "doc:billing")),
            "title": "Billing & refunds policy",
            "source_url": "https://docs.example.com/billing/refunds",
            "document_type": "markdown",
            "last_modified_at": now - timedelta(days=5),
            "days_since_modified": 5,
            "freshness_status": "fresh",
            "topic_labels": '["billing","refunds"]',
            "coverage_score": 0.92,
            "chunk_count": 14,
            "stale_chunk_count": 0,
        },
        {
            "id": str(uuid5(_NS, "doc:api")),
            "title": "Chat Completions API",
            "source_url": "https://docs.example.com/api/chat",
            "document_type": "markdown",
            "last_modified_at": now - timedelta(days=48),
            "days_since_modified": 48,
            "freshness_status": "stale",
            "topic_labels": '["api","streaming"]',
            "coverage_score": 0.61,
            "chunk_count": 22,
            "stale_chunk_count": 6,
        },
        {
            "id": str(uuid5(_NS, "doc:onboarding")),
            "title": "Product onboarding guide",
            "source_url": "https://docs.example.com/start",
            "document_type": "markdown",
            "last_modified_at": now - timedelta(days=120),
            "days_since_modified": 120,
            "freshness_status": "critical",
            "topic_labels": '["onboarding"]',
            "coverage_score": 0.4,
            "chunk_count": 9,
            "stale_chunk_count": 7,
        },
    ]
    for d in doc_specs:
        if session.scalar(select(Document).where(Document.id == d["id"])):
            continue
        session.add(
            Document(
                id=d["id"],
                pipeline_id=pipeline.id,
                title=d["title"],
                source_url=d["source_url"],
                content_hash=str(uuid5(_NS, f"hash:{d['id']}")).replace("-", "")[:64],
                document_type=d["document_type"],
                last_modified_at=d["last_modified_at"],
                ingested_at=now - timedelta(days=2),
                days_since_modified=d["days_since_modified"],
                freshness_status=d["freshness_status"],
                topic_labels=d["topic_labels"],
                coverage_score=d["coverage_score"],
                chunk_count=d["chunk_count"],
                stale_chunk_count=d["stale_chunk_count"],
            )
        )

    cfg = session.scalar(
        select(MonitoringConfig).where(MonitoringConfig.pipeline_id == pipeline.id)
    )
    if not cfg:
        cfg = MonitoringConfig(
            id=str(uuid5(_NS, "mon:cfg")),
            pipeline_id=pipeline.id,
            is_enabled=True,
            interval_minutes=60,
            probe_queries=json.dumps(
                [
                    "What is the refund window for annual plans?",
                    "Does the API support streaming responses?",
                    "How do I rotate API keys?",
                ]
            ),
            alert_trust_threshold=70.0,
            alert_hallucination_threshold=0.10,
            alert_channels=json.dumps(["dashboard"]),
            last_run_at=now - timedelta(hours=1),
            next_run_at=now + timedelta(minutes=30),
        )
        session.add(cfg)
        session.flush()

    run_id = str(uuid5(_NS, "mon:run:1"))
    if not session.scalar(select(MonitoringRun).where(MonitoringRun.id == run_id)):
        session.add(
            MonitoringRun(
                id=run_id,
                pipeline_id=pipeline.id,
                config_id=cfg.id,
                trust_score=68.5,
                hallucination_rate=0.25,
                probes_run=3,
                probes_failed=1,
                alerts_triggered=json.dumps(
                    [{"type": "trust_below_threshold", "value": 68.5, "threshold": 70.0}]
                ),
                regression_detected=True,
                run_at=now - timedelta(hours=1),
            )
        )
    run_id2 = str(uuid5(_NS, "mon:run:0"))
    if not session.scalar(select(MonitoringRun).where(MonitoringRun.id == run_id2)):
        session.add(
            MonitoringRun(
                id=run_id2,
                pipeline_id=pipeline.id,
                config_id=cfg.id,
                trust_score=74.0,
                hallucination_rate=0.12,
                probes_run=3,
                probes_failed=0,
                alerts_triggered="[]",
                regression_detected=False,
                run_at=now - timedelta(days=1),
            )
        )

    snap_specs = [
        {
            "id": str(uuid5(_NS, "snap:baseline")),
            "label": "baseline-v1.0",
            "trust_score": 0.78,
            "faithfulness_avg": 0.82,
            "context_precision_avg": 0.75,
            "hallucination_rate": 0.08,
            "trace_count": 40,
            "snapshot_at": now - timedelta(days=7),
        },
        {
            "id": str(uuid5(_NS, "snap:candidate")),
            "label": "pre-deploy-candidate",
            "trust_score": 0.71,
            "faithfulness_avg": 0.74,
            "context_precision_avg": 0.68,
            "hallucination_rate": 0.18,
            "trace_count": 36,
            "snapshot_at": now - timedelta(hours=6),
        },
    ]
    for s in snap_specs:
        if session.scalar(select(RegressionSnapshot).where(RegressionSnapshot.id == s["id"])):
            continue
        session.add(
            RegressionSnapshot(
                id=s["id"],
                pipeline_id=pipeline.id,
                snapshot_label=s["label"],
                trust_score=s["trust_score"],
                faithfulness_avg=s["faithfulness_avg"],
                context_precision_avg=s["context_precision_avg"],
                hallucination_rate=s["hallucination_rate"],
                trace_count=s["trace_count"],
                snapshot_at=s["snapshot_at"],
            )
        )

    sla_id = str(uuid5(_NS, "sla:primary"))
    if not session.scalar(select(SLAThreshold).where(SLAThreshold.id == sla_id)):
        session.add(
            SLAThreshold(
                id=sla_id,
                user_id=user.id,
                organization_id=org.id,
                pipeline_id=pipeline.id,
                trust_score_min=75.0,
                enabled=True,
            )
        )

    weekly_id = str(uuid5(_NS, "weekly:demo"))
    if not session.scalar(select(WeeklyExecutiveReport).where(WeeklyExecutiveReport.id == weekly_id)):
        session.add(
            WeeklyExecutiveReport(
                id=weekly_id,
                user_id=user.id,
                organization_id=org.id,
                recipient_email=DEMO_EMAIL,
                enabled=True,
            )
        )

    report_id = str(uuid5(_NS, "report:exec"))
    if not session.scalar(select(ReportHistory).where(ReportHistory.id == report_id)):
        payload = {
            "title": "Weekly RAG quality summary",
            "pipeline": "Demo RAG Pipeline",
            "trust_score": 0.71,
            "hallucination_rate": 0.25,
            "estimated_monthly_cost_usd": 275.0,
            "top_gaps": ["API key rotation", "Enterprise SLA uptime"],
            "period": "last_7_days",
        }
        session.add(
            ReportHistory(
                id=report_id,
                user_id=user.id,
                organization_id=org.id,
                report_type="executive",
                format="json",
                payload_json=json.dumps(payload),
            )
        )


def seed_demo_data(session: Session, *, force: bool = False) -> SeedResult:
    """Insert or refresh demo user + org + pipelines + analyzed sample traces + Phase 10 assets."""
    existing = session.scalar(select(User).where(User.email == DEMO_EMAIL))
    created = False

    if existing and force:
        for p in session.scalars(select(Pipeline).where(Pipeline.user_id == existing.id)).all():
            _purge_demo_pipeline_children(session, str(p.id))
            session.delete(p)
        for fr in session.scalars(
            select(FixRecommendation).where(FixRecommendation.user_id == existing.id)
        ).all():
            session.delete(fr)
        for key in session.scalars(select(APIKey).where(APIKey.user_id == existing.id)).all():
            session.delete(key)
        for sla in session.scalars(select(SLAThreshold).where(SLAThreshold.user_id == existing.id)).all():
            session.delete(sla)
        for wr in session.scalars(
            select(WeeklyExecutiveReport).where(WeeklyExecutiveReport.user_id == existing.id)
        ).all():
            session.delete(wr)
        for rh in session.scalars(select(ReportHistory).where(ReportHistory.user_id == existing.id)).all():
            session.delete(rh)
        user = existing
        user.password_hash = get_password_hash(DEMO_PASSWORD)
        user.name = DEMO_NAME
        user.email_verified = True
        user.onboarding_completed = True
        user.is_active = True
        user.subscription_plan = SubscriptionPlan.enterprise
        user.traces_this_month = 4
        created = True
    elif existing:
        user = existing
        user.password_hash = get_password_hash(DEMO_PASSWORD)
        user.email_verified = True
        user.onboarding_completed = True
        user.is_active = True
        user.subscription_plan = SubscriptionPlan.enterprise
    else:
        user = User(
            id=DEMO_USER_ID,
            email=DEMO_EMAIL,
            password_hash=get_password_hash(DEMO_PASSWORD),
            name=DEMO_NAME,
            role=UserRole.owner,
            is_active=True,
            subscription_plan=SubscriptionPlan.enterprise,
            email_verified=True,
            onboarding_completed=True,
            traces_this_month=4,
        )
        session.add(user)
        session.flush()
        created = True

    org = _ensure_org(session, user)

    settings = session.scalar(select(UserSettings).where(UserSettings.user_id == user.id))
    if not settings:
        session.add(
            UserSettings(
                id=DEMO_SETTINGS_ID,
                user_id=user.id,
                organization_id=org.id,
            )
        )

    pipeline, _secondary = _ensure_pipelines(session, user, org)
    api_key = _ensure_api_key(session, user, org)

    existing_traces = session.scalars(
        select(QueryTrace).where(QueryTrace.pipeline_id == pipeline.id)
    ).all()
    if force or not existing_traces:
        if existing_traces and force:
            _purge_demo_pipeline_children(session, str(pipeline.id))
        trace_count = _seed_traces(session, pipeline)
        created = True
    else:
        trace_count = len(existing_traces)

    _ensure_fix_recommendation(session, user, pipeline)
    _ensure_phase10_assets(session, user, org, pipeline)

    session.commit()

    if created:
        message = "Demo dataset seeded (core traces + Phase 10 assets)."
    else:
        message = "Demo already present; missing Phase 10 assets backfilled if needed."

    return SeedResult(
        created=created,
        user_id=str(user.id),
        pipeline_id=str(pipeline.id),
        email=DEMO_EMAIL,
        password=DEMO_PASSWORD,
        api_key=api_key,
        organization_id=str(org.id),
        trace_count=trace_count,
        message=message,
    )
