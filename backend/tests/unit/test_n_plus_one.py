"""N+1 bounds for dashboard / query list-detail (Phase 6.2)."""
from __future__ import annotations

import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.models.models import Pipeline, QueryTrace, RetrievedChunk, User
from app.repositories.pipelines import get_owned_trace_detail
from app.services.dashboard_metrics import build_dashboard_metrics, hallucination_rates_by_pipeline


@contextmanager
def count_statements(engine):
    """Count DBAPI statements on the sync engine behind an AsyncEngine."""
    counter = {"n": 0}

    def _before(conn, cursor, statement, parameters, context, executemany):
        counter["n"] += 1

    sync_engine = engine.sync_engine
    event.listen(sync_engine, "before_cursor_execute", _before)
    try:
        yield counter
    finally:
        event.remove(sync_engine, "before_cursor_execute", _before)


@pytest_asyncio.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session, engine
    await engine.dispose()


async def _seed_user_with_pipelines(session: AsyncSession, n_pipelines: int) -> User:
    user = User(
        id=str(uuid.uuid4()),
        email=f"nplus{n_pipelines}@example.com",
        password_hash="x",
        name="N Plus",
    )
    session.add(user)
    await session.flush()
    for i in range(n_pipelines):
        pid = str(uuid.uuid4())
        session.add(
            Pipeline(
                id=pid,
                user_id=user.id,
                name=f"p{i}",
                queries_per_month=1000,
                cost_per_wrong_answer_usd=5.0,
            )
        )
        session.add(
            QueryTrace(
                id=str(uuid.uuid4()),
                pipeline_id=pid,
                query_text=f"q{i}",
                is_hallucination=(i % 2 == 0),
                faithfulness_score=0.8,
                grounded_fraction=0.7,
                context_precision_score=0.6,
                traced_at=datetime.now(timezone.utc),
                analysis_status="complete",
            )
        )
    await session.commit()
    return user


@pytest.mark.asyncio
async def test_hallucination_rates_single_grouped_query(db_session):
    session, engine = db_session
    user = await _seed_user_with_pipelines(session, 5)
    pids = [
        str(r)
        for r in (
            await session.execute(select(Pipeline.id).where(Pipeline.user_id == user.id))
        ).scalars().all()
    ]
    with count_statements(engine) as counter:
        rates = await hallucination_rates_by_pipeline(session, pids)
    assert len(rates) == 5
    assert counter["n"] == 1


@pytest.mark.asyncio
async def test_dashboard_query_count_does_not_scale_with_pipelines(db_session):
    session, engine = db_session

    user_small = await _seed_user_with_pipelines(session, 2)
    with count_statements(engine) as c_small:
        await build_dashboard_metrics(session, user_small)
    small_n = c_small["n"]

    user_large = await _seed_user_with_pipelines(session, 8)
    with count_statements(engine) as c_large:
        await build_dashboard_metrics(session, user_large)
    large_n = c_large["n"]

    # Must not grow linearly with pipeline count (old N+1 was +2 per pipeline).
    assert large_n <= small_n + 2
    assert large_n <= 20


@pytest.mark.asyncio
async def test_trace_detail_eager_loads_without_ownership_extra_query(db_session):
    session, engine = db_session
    user = await _seed_user_with_pipelines(session, 1)
    pid = (
        await session.execute(select(Pipeline.id).where(Pipeline.user_id == user.id))
    ).scalar_one()
    tid = str(uuid.uuid4())
    session.add(
        QueryTrace(
            id=tid,
            pipeline_id=pid,
            query_text="detail",
            analysis_status="complete",
            traced_at=datetime.now(timezone.utc),
        )
    )
    session.add(
        RetrievedChunk(
            id=str(uuid.uuid4()),
            trace_id=tid,
            chunk_id="c1",
            chunk_text="chunk",
            similarity_score=0.9,
            bm25_score=0.5,
            rank=1,
        )
    )
    await session.commit()

    with count_statements(engine) as counter:
        trace = await get_owned_trace_detail(session, user, tid)
    assert trace is not None
    assert len(trace.retrieved_chunks) == 1
    assert trace.pipeline is not None
    # Parent + selectinload for chunks/grounding/pipeline — bounded, no O(children) loop queries
    assert counter["n"] <= 5
