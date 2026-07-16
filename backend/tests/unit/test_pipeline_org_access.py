"""Org-scoped pipeline access helpers."""

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from app.repositories.pipelines import (
    require_owned_pipeline,
    require_pipeline_owner,
    user_can_access_pipeline,
)


def _run(coro):
    return asyncio.run(coro)


@pytest.fixture
def owner():
    return SimpleNamespace(id="user-owner", organization_id="org-1")


@pytest.fixture
def teammate():
    return SimpleNamespace(id="user-mate", organization_id="org-1")


@pytest.fixture
def outsider():
    return SimpleNamespace(id="user-out", organization_id="org-2")


@pytest.fixture
def pipeline():
    return SimpleNamespace(
        id="pipe-1",
        user_id="user-owner",
        organization_id="org-1",
    )


def test_owner_can_access(owner, pipeline):
    db = AsyncMock()
    assert _run(user_can_access_pipeline(db, owner, pipeline)) is True


def test_org_member_can_access(teammate, pipeline):
    db = AsyncMock()
    # accepted membership id returned
    result = MagicMock()
    result.scalar_one_or_none.return_value = "member-id"
    db.execute = AsyncMock(return_value=result)
    assert _run(user_can_access_pipeline(db, teammate, pipeline)) is True


def test_outsider_denied(outsider, pipeline):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    assert _run(user_can_access_pipeline(db, outsider, pipeline)) is False


def test_require_pipeline_owner_rejects_teammate(teammate, pipeline):
    db = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    db.execute = AsyncMock(return_value=result)
    with pytest.raises(HTTPException) as exc:
        _run(require_pipeline_owner(db, teammate, pipeline.id))
    assert exc.value.status_code == 404


def test_require_owned_pipeline_allows_org_member(teammate, pipeline):
    db = AsyncMock()

    pipe_result = MagicMock()
    pipe_result.scalar_one_or_none.return_value = pipeline
    member_result = MagicMock()
    member_result.scalar_one_or_none.return_value = "member-id"

    db.execute = AsyncMock(side_effect=[pipe_result, member_result])
    found = _run(require_owned_pipeline(db, teammate, pipeline.id))
    assert found is pipeline
