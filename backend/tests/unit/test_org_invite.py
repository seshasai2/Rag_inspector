"""Tests for organization member invite semantics."""
import uuid
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.models.models import Base, Organization, OrganizationMember, User, UserRole


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def _make_user(email: str, org_id: str | None = None) -> User:
    return User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash="hashed",
        name=email.split("@")[0],
        role=UserRole.owner,
        organization_id=org_id,
    )


def test_pending_invite_stores_invitee_not_inviter(db_session: Session):
    org = Organization(
        id=str(uuid.uuid4()),
        name="Acme",
        slug="acme",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    inviter = _make_user("owner@acme.com", org.id)
    invitee = _make_user("eng@acme.com")
    db_session.add_all([org, inviter, invitee])
    db_session.commit()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=invitee.id,
        role=UserRole.viewer,
        invited_email=invitee.email,
        accepted_at=None,
    )
    db_session.add(member)
    db_session.commit()

    stored = db_session.query(OrganizationMember).one()
    assert stored.user_id == invitee.id
    assert stored.user_id != inviter.id
    assert stored.invited_email == "eng@acme.com"
    assert stored.accepted_at is None


def test_pending_invite_allows_null_user_id(db_session: Session):
    org = Organization(
        id=str(uuid.uuid4()),
        name="Acme",
        slug="acme-2",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(org)
    db_session.commit()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=None,
        role=UserRole.viewer,
        invited_email="newhire@acme.com",
        accepted_at=None,
    )
    db_session.add(member)
    db_session.commit()

    stored = db_session.query(OrganizationMember).one()
    assert stored.user_id is None
    assert stored.invited_email == "newhire@acme.com"
