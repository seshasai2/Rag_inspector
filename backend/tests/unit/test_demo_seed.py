"""Demo seed script (Phase 7.3 + Phase 10 assets)."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.security import hash_api_key, verify_password
from app.db.session import Base
from app.models.models import (
    APIKey,
    Document,
    KnowledgeGap,
    MonitoringConfig,
    MonitoringRun,
    Organization,
    Pipeline,
    QueryTrace,
    RegressionSnapshot,
    ReportHistory,
    User,
)
from app.services.demo_seed import (
    DEMO_API_KEY,
    DEMO_EMAIL,
    DEMO_ORG_SLUG,
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
    assert result.api_key == DEMO_API_KEY
    assert result.trace_count == 4

    user = session.scalar(select(User).where(User.email == DEMO_EMAIL))
    assert user is not None
    assert user.email_verified is True
    assert verify_password(DEMO_PASSWORD, user.password_hash)
    assert user.organization_id is not None
    assert user.subscription_plan.value == "enterprise"

    org = session.scalar(select(Organization).where(Organization.slug == DEMO_ORG_SLUG))
    assert org is not None

    pipes = session.scalars(select(Pipeline).where(Pipeline.user_id == user.id)).all()
    assert len(pipes) == 2
    traces = session.scalars(
        select(QueryTrace).where(QueryTrace.pipeline_id == result.pipeline_id)
    ).all()
    assert len(traces) == 4
    assert all(t.analysis_status == "completed" for t in traces)
    assert any(t.is_hallucination for t in traces)

    key = session.scalar(select(APIKey).where(APIKey.key_hash == hash_api_key(DEMO_API_KEY)))
    assert key is not None
    assert key.is_active is True


def test_seed_phase10_assets(session: Session):
    result = seed_demo_data(session)
    assert session.scalars(select(KnowledgeGap)).all()
    assert session.scalars(select(Document)).all()
    assert session.scalar(select(MonitoringConfig).where(MonitoringConfig.pipeline_id == result.pipeline_id))
    assert session.scalars(select(MonitoringRun)).all()
    assert session.scalars(select(RegressionSnapshot)).all()
    assert session.scalars(select(ReportHistory)).all()


def test_seed_is_idempotent(session: Session):
    first = seed_demo_data(session)
    second = seed_demo_data(session)
    assert first.created is True
    assert second.created is False
    users = session.scalars(select(User).where(User.email == DEMO_EMAIL)).all()
    assert len(users) == 1
    traces = session.scalars(select(QueryTrace)).all()
    assert len(traces) == 4
    # Phase 10 rows remain stable (no duplicates)
    assert len(session.scalars(select(KnowledgeGap)).all()) == 2
    assert len(session.scalars(select(Document)).all()) == 3


def test_seed_force_refreshes(session: Session):
    seed_demo_data(session)
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
    assert any(tr.id == old_id for tr in traces)
    assert len(session.scalars(select(KnowledgeGap)).all()) == 2


def test_seed_backfills_phase10_without_force(session: Session):
    """Older demos with traces only should gain Phase 10 rows on re-seed."""
    seed_demo_data(session)
    for gap in session.scalars(select(KnowledgeGap)).all():
        session.delete(gap)
    session.commit()
    assert not session.scalars(select(KnowledgeGap)).all()

    result = seed_demo_data(session, force=False)
    assert result.created is False
    assert len(session.scalars(select(KnowledgeGap)).all()) == 2
