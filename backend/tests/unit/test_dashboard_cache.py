"""Optional Redis dashboard aggregate cache (Phase 6.5)."""
from __future__ import annotations

import time
from typing import Any, Optional
from unittest.mock import patch

import pytest

from app.core import redis_cache
from app.services import dashboard_cache


class _FakeRedis:
    """Minimal async Redis stand-in for ``cache_get_json_async`` / ``cache_set_json_async``."""

    def __init__(self) -> None:
        self.store: dict[str, tuple[str, float | None]] = {}

    async def get(self, key: str) -> Optional[str]:
        item = self.store.get(key)
        if item is None:
            return None
        value, expires = item
        if expires is not None and time.time() > expires:
            del self.store[key]
            return None
        return value

    async def set(self, key: str, value: str, ex: int | None = None) -> bool:
        expires = time.time() + ex if ex is not None else None
        self.store[key] = (value, expires)
        return True

    def ping(self) -> bool:
        return True

    def close(self) -> None:
        pass


@pytest.fixture(autouse=True)
def _reset_cache(monkeypatch):
    redis_cache.reset_redis_cache_for_tests()
    monkeypatch.setattr(
        "app.core.config.settings.DASHBOARD_METRICS_CACHE_ENABLED",
        True,
        raising=False,
    )
    monkeypatch.setattr(
        "app.core.config.settings.DASHBOARD_METRICS_CACHE_TTL_SECONDS",
        30,
        raising=False,
    )
    yield
    redis_cache.reset_redis_cache_for_tests()


@pytest.mark.asyncio
async def test_get_or_set_json_hit_miss_and_latency():
    fake = _FakeRedis()
    with patch.object(redis_cache, "_get_async_client", return_value=fake):
        calls = {"n": 0}

        async def factory() -> dict[str, Any]:
            calls["n"] += 1
            await _sleep_ms(40)
            return {"total_queries": 7, "ok": True}

        t0 = time.perf_counter()
        miss_val, miss_status = await dashboard_cache.get_or_set_json("k1", factory)
        miss_ms = (time.perf_counter() - t0) * 1000
        assert miss_status == "miss"
        assert miss_val["total_queries"] == 7
        assert calls["n"] == 1
        assert miss_ms >= 35

        t1 = time.perf_counter()
        hit_val, hit_status = await dashboard_cache.get_or_set_json("k1", factory)
        hit_ms = (time.perf_counter() - t1) * 1000
        assert hit_status == "hit"
        assert hit_val == miss_val
        assert calls["n"] == 1
        # Cache hit skips the factory sleep — measurable win
        assert hit_ms < miss_ms / 2
        assert hit_ms < 20


@pytest.mark.asyncio
async def test_cache_bypass_when_disabled(monkeypatch):
    monkeypatch.setattr(
        "app.core.config.settings.DASHBOARD_METRICS_CACHE_ENABLED",
        False,
        raising=False,
    )
    calls = {"n": 0}

    async def factory():
        calls["n"] += 1
        return {"a": 1}

    val, status = await dashboard_cache.get_or_set_json("k", factory)
    assert status == "bypass"
    assert val == {"a": 1}
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_cache_fail_open_when_redis_down():
    with patch.object(redis_cache, "_get_async_client", return_value=None):
        calls = {"n": 0}

        async def factory():
            calls["n"] += 1
            return {"x": 2}

        v1, s1 = await dashboard_cache.get_or_set_json("k", factory)
        v2, s2 = await dashboard_cache.get_or_set_json("k", factory)
        assert s1 == "miss" and s2 == "miss"
        assert v1 == v2 == {"x": 2}
        assert calls["n"] == 2


def test_dashboard_cache_keys_are_scoped():
    k1 = dashboard_cache.timeseries_cache_key("u1", None, "faithfulness_score", 30)
    k2 = dashboard_cache.timeseries_cache_key("u1", "p1", "faithfulness_score", 30)
    k3 = dashboard_cache.timeseries_cache_key("u2", None, "faithfulness_score", 30)
    assert k1 != k2 != k3
    assert "raginspector:dash" in k1


async def _sleep_ms(ms: int) -> None:
    import asyncio

    await asyncio.sleep(ms / 1000)
