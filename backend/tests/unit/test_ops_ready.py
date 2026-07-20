"""Compose / ops readiness helpers (Phase 7.2)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.responses import JSONResponse

from app.api.v1.endpoints import ops


@pytest.mark.asyncio
async def test_readiness_returns_200_when_checks_ok():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    fake_redis = MagicMock()
    fake_redis.ping.return_value = True
    with patch("app.api.v1.endpoints.ops.Redis.from_url", return_value=fake_redis):
        resp = await ops.readiness(db=db)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 200
    assert resp.body and b'"status":"ready"' in resp.body


@pytest.mark.asyncio
async def test_readiness_returns_503_when_redis_down():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    with (
        patch("app.api.v1.endpoints.ops._redis_optional_for_seed_demo", return_value=False),
        patch(
            "app.api.v1.endpoints.ops.Redis.from_url",
            side_effect=ConnectionError("down"),
        ),
    ):
        resp = await ops.readiness(db=db)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 503
    assert b'"status":"degraded"' in resp.body


@pytest.mark.asyncio
async def test_readiness_skips_redis_in_development_seed_demo():
    db = AsyncMock()
    db.execute = AsyncMock(return_value=None)
    with (
        patch("app.api.v1.endpoints.ops._redis_optional_for_seed_demo", return_value=True),
        patch(
            "app.api.v1.endpoints.ops.Redis.from_url",
            side_effect=ConnectionError("down"),
        ),
        patch(
            "app.api.v1.endpoints.ops.collect_backlog_snapshot",
            new_callable=AsyncMock,
            return_value={"analysis_jobs": {"pending": 0, "running": 0}},
        ),
    ):
        resp = await ops.readiness(db=db)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 200
    assert b'"redis":"skipped"' in resp.body
