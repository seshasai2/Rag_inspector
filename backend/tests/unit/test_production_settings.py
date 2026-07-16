"""Production settings fail-closed validation (Phase 8.7)."""
from __future__ import annotations

import pytest

from app.core.config import validate_production_settings


def _ok(**overrides):
    base = dict(
        environment="production",
        secret_key="a" * 32,
        frontend_url="https://app.example.com",
        allowed_hosts="app.example.com,api.example.com",
        database_url="postgresql+asyncpg://u:strongpass@db:5432/raginspector",
        redis_url="redis://:strongpass@redis:6379/0",
        ops_shared_token="ops-token-min-16-chars",
    )
    base.update(overrides)
    validate_production_settings(**base)


def test_non_production_is_noop():
    validate_production_settings(
        environment="development",
        secret_key="short",
        frontend_url="http://localhost:3000",
        allowed_hosts="localhost",
        database_url="postgresql+asyncpg://raginspector:raginspector_secret@localhost:5432/x",
        redis_url="redis://:redis_secret@localhost:6379/0",
    )


def test_production_accepts_strong_config():
    _ok(ops_shared_token="ops-token-min-16-chars")


def test_production_rejects_missing_ops_token():
    with pytest.raises(RuntimeError, match="OPS_SHARED_TOKEN"):
        _ok(ops_shared_token="")


def test_production_rejects_weak_secret():
    with pytest.raises(RuntimeError, match="SECRET_KEY"):
        _ok(secret_key="too-short")


def test_production_rejects_http_frontend():
    with pytest.raises(RuntimeError, match="FRONTEND_URL"):
        _ok(frontend_url="http://app.example.com")


def test_production_rejects_localhost_hosts():
    with pytest.raises(RuntimeError, match="ALLOWED_HOSTS"):
        _ok(allowed_hosts="localhost")


def test_production_rejects_default_db_password():
    with pytest.raises(RuntimeError, match="default development password"):
        _ok(database_url="postgresql+asyncpg://u:raginspector_secret@db:5432/raginspector")


def test_production_rejects_default_redis_password():
    with pytest.raises(RuntimeError, match="REDIS_URL"):
        _ok(redis_url="redis://:redis_secret@redis:6379/0")
