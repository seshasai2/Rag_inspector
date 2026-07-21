"""Ops seed-demo endpoint (portfolio / interview)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_seed_demo_allowed_in_development(monkeypatch):
    from app.core.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "OPS_SHARED_TOKEN", "test-ops-token-16chars")

    fake_result = MagicMock(
        created=True,
        message="seeded",
        email="demo@example.com",
        password="DemoPass123!",
        pipeline_id="pipe-1",
        organization_id="org-1",
        trace_count=4,
        api_key="ri-demo",
    )

    with patch("app.services.demo_seed.seed_demo_data", return_value=fake_result):
        with patch("app.db.session.sync_engine"):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                resp = await client.post("/api/v1/ops/seed-demo?force=true")

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["email"] == "demo@example.com"
    assert body["trace_count"] == 4


@pytest.mark.asyncio
async def test_seed_demo_blocked_in_production_without_token(monkeypatch):
    from app.core.config import settings
    from app.main import app

    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "OPS_SHARED_TOKEN", "test-ops-token-16chars")

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post("/api/v1/ops/seed-demo")
    assert resp.status_code == 401
