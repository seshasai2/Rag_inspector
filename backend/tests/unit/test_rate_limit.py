"""Rate-limit enforcement for auth + ingest (Phase 5.1)."""
from __future__ import annotations

import inspect

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core import rate_limit as rl


def test_auth_and_ingest_limit_constants_are_set():
    assert rl.AUTH_REGISTER_LIMIT == "10/minute"
    assert rl.AUTH_LOGIN_LIMIT == "20/minute"
    assert rl.AUTH_PASSWORD_RESET_LIMIT == "5/minute"
    assert rl.AUTH_REFRESH_LIMIT == "30/minute"
    assert rl.AUTH_RESEND_VERIFY_LIMIT == "5/minute"
    assert rl.AUTH_VERIFY_EMAIL_LIMIT == "20/minute"
    assert rl.INGEST_TRACE_LIMIT == "120/minute"
    assert rl.INGEST_BATCH_LIMIT == "30/minute"


def test_slowapi_returns_429_when_limit_exceeded():
    """Prove SlowAPI rejects excess requests with HTTP 429 (limits enforced)."""
    limiter = Limiter(key_func=get_remote_address, enabled=True, default_limits=[])
    app = FastAPI()
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)

    @app.get("/ping")
    @limiter.limit("2/minute")
    async def ping(request: Request):
        return {"ok": True}

    client = TestClient(app)
    assert client.get("/ping").status_code == 200
    assert client.get("/ping").status_code == 200
    blocked = client.get("/ping")
    assert blocked.status_code == 429


def test_auth_and_ingest_routes_accept_request_for_slowapi():
    from app.api.v1.endpoints import auth, ingest, traces

    for fn in (
        auth.register,
        auth.login,
        auth.login_mfa,
        auth.refresh,
        auth.forgot_password,
        auth.reset_password,
        auth.resend_verification,
        auth.verify_email,
        ingest.ingest_trace,
        traces.ingest_trace_batch,
    ):
        params = inspect.signature(fn).parameters
        assert "request" in params, f"{fn.__name__} must accept Request for SlowAPI"
