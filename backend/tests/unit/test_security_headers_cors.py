"""Security headers + CORS policy (Phase 5.7)."""
from __future__ import annotations

from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core import security_http as sh


def test_production_cors_is_locked_to_frontend_url():
    kwargs = sh.cors_middleware_kwargs(
        is_production=True,
        frontend_url="https://app.example.com/",
    )
    assert kwargs["allow_origins"] == ["https://app.example.com"]
    assert kwargs["allow_origin_regex"] is None
    assert kwargs["allow_methods"] == sh.PROD_CORS_METHODS
    assert kwargs["allow_headers"] == sh.PROD_CORS_HEADERS
    assert kwargs["expose_headers"] == sh.PROD_CORS_EXPOSE_HEADERS
    assert "*" not in kwargs["allow_methods"]
    assert "*" not in kwargs["allow_headers"]


def test_dev_cors_allows_localhost_and_regex():
    kwargs = sh.cors_middleware_kwargs(
        is_production=False,
        frontend_url="http://localhost:3000",
    )
    assert "http://localhost:3000" in kwargs["allow_origins"]
    assert kwargs["allow_origin_regex"]
    assert kwargs["allow_methods"] == ["*"]


def test_apply_security_headers_always_sets_core():
    response = MagicMock()
    response.headers = {}
    sh.apply_security_headers(response, is_production=False)
    for key in sh.API_SECURITY_HEADERS:
        assert response.headers[key] == sh.API_SECURITY_HEADERS[key]
    assert "Strict-Transport-Security" not in response.headers


def test_apply_security_headers_adds_hsts_in_production():
    response = MagicMock()
    response.headers = {}
    sh.apply_security_headers(response, is_production=True)
    assert response.headers["Strict-Transport-Security"] == sh.HSTS_HEADER


def test_live_app_emits_security_headers():
    """Smoke: middleware helper attaches nosniff / DENY / HSTS in production mode."""
    probe = FastAPI()

    @probe.middleware("http")
    async def _headers(request, call_next):
        response = await call_next(request)
        return sh.apply_security_headers(response, is_production=True)

    @probe.get("/ping")
    async def ping():
        return {"ok": True}

    c = TestClient(probe)
    resp = c.get("/ping")
    assert resp.status_code == 200
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["strict-transport-security"] == sh.HSTS_HEADER
    assert "frame-ancestors 'none'" in resp.headers["content-security-policy"]
