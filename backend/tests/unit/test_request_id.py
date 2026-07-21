"""Request ID middleware + helpers (Phase 8.3)."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.core.request_id import normalize_request_id
from app.services import analysis_queue as aq


def test_normalize_request_id_accepts_safe_client_value():
    assert normalize_request_id("client-req-abc123") == "client-req-abc123"


def test_normalize_request_id_rejects_junk():
    rid = normalize_request_id("bad id with spaces!")
    assert rid != "bad id with spaces!"
    assert len(rid) >= 8


def test_middleware_echoes_and_mints_request_id():
    from app.main import app

    client = TestClient(app)
    minted = client.get("/health")
    assert minted.status_code == 200
    assert minted.headers.get("x-request-id")

    custom = client.get("/health", headers={"X-Request-ID": "trace-from-client-01"})
    assert custom.headers.get("x-request-id") == "trace-from-client-01"


def test_live_alias_matches_health():
    from app.main import app

    client = TestClient(app)
    live = client.get("/live").json()
    health = client.get("/health").json()
    # Timestamp is generated per request — compare stable liveness fields only.
    assert live["status"] == health["status"] == "healthy"
    assert live["service"] == health["service"] == "raginspector"
    assert live["version"] == health["version"]
    assert "timestamp" in live and "timestamp" in health


def test_enqueue_passes_request_id_header():
    clear_contextvars()
    bind_contextvars(request_id="req-from-api-xyz")
    fake_task = MagicMock()
    fake_task.id = "celery-1"
    with patch("app.workers.tasks.run_analysis") as run:
        run.apply_async.return_value = fake_task
        assert aq.enqueue_analysis("trace-1") == "celery-1"
        run.apply_async.assert_called_once()
        kwargs = run.apply_async.call_args.kwargs
        assert kwargs["headers"]["request_id"] == "req-from-api-xyz"
    clear_contextvars()
