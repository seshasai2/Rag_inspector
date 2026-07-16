"""Optional Sentry init (Phase 8.6)."""
from __future__ import annotations

from unittest.mock import patch

from app.core import sentry_init as si


def test_init_sentry_noop_without_dsn(monkeypatch):
    monkeypatch.setattr(si.settings, "SENTRY_DSN", None)
    with patch("sentry_sdk.init") as init:
        assert si.init_sentry() is False
        init.assert_not_called()


def test_init_sentry_calls_sdk_with_fastapi_integrations(monkeypatch):
    monkeypatch.setattr(si.settings, "SENTRY_DSN", "https://key@example.com/1")
    monkeypatch.setattr(si.settings, "ENVIRONMENT", "development")
    with patch("sentry_sdk.init") as init, patch(
        "sentry_sdk.integrations.fastapi.FastApiIntegration",
        return_value="fastapi",
    ), patch(
        "sentry_sdk.integrations.starlette.StarletteIntegration",
        return_value="starlette",
    ):
        assert si.init_sentry(celery=False) is True
        init.assert_called_once()
        kwargs = init.call_args.kwargs
        assert kwargs["dsn"] == "https://key@example.com/1"
        assert "fastapi" in kwargs["integrations"]
        assert "starlette" in kwargs["integrations"]
        assert kwargs["traces_sample_rate"] == 1.0


def test_init_sentry_celery_integration(monkeypatch):
    monkeypatch.setattr(si.settings, "SENTRY_DSN", "https://key@example.com/1")
    monkeypatch.setattr(si.settings, "ENVIRONMENT", "production")
    with patch("sentry_sdk.init") as init, patch(
        "sentry_sdk.integrations.celery.CeleryIntegration",
        return_value="celery",
    ):
        assert si.init_sentry(celery=True) is True
        assert init.call_args.kwargs["integrations"] == ["celery"]
        assert init.call_args.kwargs["traces_sample_rate"] == 0.1
