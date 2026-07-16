"""Optional OpenTelemetry bootstrap (fail-open).

When ``OTEL_EXPORTER_OTLP_ENDPOINT`` is set and ``opentelemetry-*`` packages are
installed, FastAPI + HTTPX instrumentation is enabled. Otherwise this module is
a no-op so production Compose stays dependency-light by default.
"""

from __future__ import annotations

import os
from typing import Any

import structlog

logger = structlog.get_logger()
_initialized = False


def init_otel(service_name: str = "raginspector-api") -> bool:
    """Initialize OTel if configured. Returns True when tracing was enabled."""
    global _initialized
    if _initialized:
        return True
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT", "").strip()
    if not endpoint:
        return False
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Presence check for FastAPI instrumentor (used in instrument_fastapi).
        import opentelemetry.instrumentation.fastapi  # noqa: F401
    except ImportError:
        logger.warning("otel_packages_missing", endpoint=endpoint)
        return False

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    # FastAPIInstrumentor.instrument_app is called from main after app exists.
    _initialized = True
    logger.info("otel_initialized", service=service_name, endpoint=endpoint)
    return True


def instrument_fastapi(app: Any) -> None:
    """Attach FastAPI instrumentation when OTel was initialized."""
    if not _initialized:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("otel_fastapi_instrument_failed", error=str(exc))
