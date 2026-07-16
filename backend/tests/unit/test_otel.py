"""OpenTelemetry optional bootstrap."""

import builtins

from app.core import otel


def test_init_otel_skips_without_endpoint(monkeypatch):
    otel._initialized = False
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert otel.init_otel() is False


def test_init_otel_graceful_without_packages(monkeypatch):
    otel._initialized = False
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("opentelemetry"):
            raise ImportError("otel packages not installed")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert otel.init_otel() is False


def test_instrument_fastapi_noop_when_uninitialized():
    otel._initialized = False
    otel.instrument_fastapi(object())  # must not raise
