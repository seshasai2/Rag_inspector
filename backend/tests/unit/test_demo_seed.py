"""Demo seed script (Phase 7.3)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.db.session import Base
from app.models.models import Pipeline, QueryTrace, User
from app.services.demo_seed import (
    DEMO_EMAIL,
    DEMO_PASSWORD,
    seed_demo_data,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def test_seed_creates_demo_user_pipeline_and_traces(session: Session):
    result = seed_demo_data(session, force=False)
    assert result.created is True
    assert result.email == DEMO_EMAIL
    assert result.trace_count == 4

    user = session.scalar(select(User).where(User.email == DEMO_EMAIL))
    assert user is not None
    assert user.email_verified is True
    assert verify_password(DEMO_PASSWORD, user.password_hash)

    pipes = session.scalars(select(Pipeline).where(Pipeline.user_id == user.id)).all()
    assert len(pipes) == 1
    traces = session.scalars(
        select(QueryTrace).where(QueryTrace.pipeline_id == pipes[0].id)
    ).all()
    assert len(traces) == 4
    assert all(t.analysis_status == "completed" for t in traces)
    assert any(t.is_hallucination for t in traces)


def test_seed_is_idempotent(session: Session):
    first = seed_demo_data(session)
    second = seed_demo_data(session)
    assert first.created is True
    assert second.created is False
    users = session.scalars(select(User).where(User.email == DEMO_EMAIL)).all()
    assert len(users) == 1
    traces = session.scalars(select(QueryTrace)).all()
    assert len(traces) == 4


def test_seed_force_refreshes(session: Session):
    seed_demo_data(session)
    # Mutate a trace so we can detect refresh
    t = session.scalars(select(QueryTrace)).first()
    assert t is not None
    old_id = t.id
    t.query_text = "mutated"
    session.commit()

    result = seed_demo_data(session, force=True)
    assert result.created is True
    traces = session.scalars(select(QueryTrace)).all()
    assert len(traces) == 4
    assert all(tr.query_text != "mutated" for tr in traces)
    # Stable IDs restored
    assert any(tr.id == old_id for tr in traces)
