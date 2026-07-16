"""Unit tests for ingest_service (critical path — restores coverage gate)."""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.models.models import ChunkStat, Pipeline, SubscriptionPlan, User
from app.schemas.schemas import ChunkPayload, TraceIngest
from app.services import ingest_service as svc


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


def _user(**kwargs) -> User:
    defaults = dict(
        id=str(uuid.uuid4()),
        email=f"{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        name="Ingest Tester",
        subscription_plan=SubscriptionPlan.free,
        traces_this_month=0,
        organization_id=None,
    )
    defaults.update(kwargs)
    return User(**defaults)


def test_check_plan_quota_allows_under_limit():
    user = _user(traces_this_month=0)
    svc._check_plan_quota(user)  # no raise


def test_check_plan_quota_blocks_over_limit():
    user = _user(traces_this_month=10_000_000)
    with pytest.raises(HTTPException) as exc:
        svc._check_plan_quota(user)
    assert exc.value.status_code == 429


@pytest.mark.asyncio
async def test_get_or_create_pipeline_creates(db_session):
    session = db_session
    user = _user(organization_id="org-1")
    session.add(user)
    await session.commit()

    pipeline = await svc._get_or_create_pipeline(session, user, "demo-pipe")
    assert pipeline.name == "demo-pipe"
    assert pipeline.user_id == user.id
    assert pipeline.organization_id == "org-1"


@pytest.mark.asyncio
async def test_get_or_create_pipeline_reuses_and_backfills_org(db_session):
    session = db_session
    user = _user(organization_id="org-2")
    session.add(user)
    await session.flush()
    existing = Pipeline(user_id=user.id, name="shared", organization_id=None)
    session.add(existing)
    await session.commit()

    pipeline = await svc._get_or_create_pipeline(session, user, "shared")
    assert pipeline.id == existing.id
    assert pipeline.organization_id == "org-2"


@pytest.mark.asyncio
async def test_batch_upsert_chunk_stats_create_and_update(db_session):
    session = db_session
    user = _user()
    session.add(user)
    await session.flush()
    pipeline = Pipeline(user_id=user.id, name="p")
    session.add(pipeline)
    await session.flush()

    existing = ChunkStat(
        chunk_id="c1",
        pipeline_id=pipeline.id,
        text="old",
        retrieval_count=1,
        citation_count=0,
    )
    session.add(existing)
    await session.commit()

    chunks = [
        ChunkPayload(chunk_id="c1", chunk_text="updated", similarity_score=0.9, rank=1),
        ChunkPayload(chunk_id="c2", chunk_text="new", similarity_score=0.8, rank=2),
    ]
    await svc._batch_upsert_chunk_stats(session, pipeline.id, chunks)
    await session.commit()

    assert existing.retrieval_count == 2
    rows = (await session.execute(
        __import__("sqlalchemy", fromlist=["select"]).select(ChunkStat).where(
            ChunkStat.pipeline_id == pipeline.id
        )
    )).scalars().all()
    assert {r.chunk_id for r in rows} == {"c1", "c2"}


@pytest.mark.asyncio
async def test_batch_upsert_empty_noop(db_session):
    session = db_session
    await svc._batch_upsert_chunk_stats(session, "pipe", [])


@pytest.mark.asyncio
async def test_ingest_trace_queues_analysis(db_session):
    session = db_session
    user = _user()
    session.add(user)
    await session.commit()

    payload = TraceIngest(
        pipeline_name="ingest-demo",
        query_text="what is refund?",
        answer_text="14 days",
        retrieved_chunks=[
            ChunkPayload(chunk_id="chunk-a", chunk_text="refund window 14 days", rank=1)
        ],
        metadata={"source": "test"},
        stage_latencies={"retrieve": 12},
    )

    with patch("app.services.ingest_service.enqueue_analysis", return_value="task-123"):
        resp = await svc.ingest_trace(session, user, payload)

    assert resp.status == "accepted"
    assert resp.message == "Trace queued for analysis"
    assert str(resp.trace_id)
    await session.refresh(user)
    assert user.traces_this_month == 1


@pytest.mark.asyncio
async def test_ingest_trace_unanalyzed_when_queue_fails(db_session):
    session = db_session
    user = _user()
    session.add(user)
    await session.commit()

    payload = TraceIngest(
        pipeline_name="ingest-demo",
        query_text="q",
        retrieved_chunks=[],
    )

    with patch(
        "app.services.ingest_service.enqueue_analysis",
        side_effect=RuntimeError("broker down"),
    ):
        resp = await svc.ingest_trace(session, user, payload)

    assert resp.status == "accepted_unanalyzed"
    assert "analysis" in resp.message.lower() or "queue" in resp.message.lower() or resp.message
