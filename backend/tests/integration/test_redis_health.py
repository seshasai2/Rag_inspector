"""Integration: Redis health via ops readiness and direct ping."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_redis_ping_or_skip(redis_available):
    """Direct Redis PING — skip cleanly when broker is not running locally."""
    if not redis_available:
        pytest.skip("Redis not available at REDIS_URL")

    from redis import Redis

    from app.core.config import settings

    client = Redis.from_url(
        settings.REDIS_URL,
        socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
        socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
    )
    try:
        assert client.ping() is True
    finally:
        client.close()


@pytest.mark.asyncio
async def test_ops_ready_reports_redis_ok_when_available(client: AsyncClient, redis_available: bool):
    if not redis_available:
        pytest.skip("Redis not available at REDIS_URL")

    resp = await client.get("/api/v1/ops/ready")
    assert resp.status_code in (200, 503)
    body = resp.json()
    assert "checks" in body
    assert body["checks"]["redis"] == "ok"
    if body["checks"]["database"] == "ok":
        assert resp.status_code == 200
        assert body["status"] == "ready"


@pytest.mark.asyncio
async def test_ops_ready_degraded_when_redis_down(client: AsyncClient):
    """Force Redis failure and expect degraded readiness when Redis is required."""
    with (
        patch("app.api.v1.endpoints.ops._redis_optional_for_seed_demo", return_value=False),
        patch(
            "app.api.v1.endpoints.ops.Redis.from_url",
            side_effect=ConnectionError("redis unavailable"),
        ),
    ):
        resp = await client.get("/api/v1/ops/ready")

    assert resp.status_code == 503
    body = resp.json()
    assert body["status"] == "degraded"
    assert body["checks"]["redis"].startswith("error:")


@pytest.mark.asyncio
async def test_ops_ready_ok_with_mocked_redis(client: AsyncClient):
    fake = MagicMock()
    fake.ping.return_value = True
    with patch("app.api.v1.endpoints.ops.Redis.from_url", return_value=fake):
        with patch(
            "app.api.v1.endpoints.ops.collect_backlog_snapshot",
            return_value={
                "analysis_jobs": {"pending": 0, "running": 0},
                "redis_ok": True,
                "celery_queue_depths": {"analysis": 0, "celery": 0},
            },
        ):
            resp = await client.get("/api/v1/ops/ready")

    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["redis"] == "ok"
    fake.close.assert_called()
