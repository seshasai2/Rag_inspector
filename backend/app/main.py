import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

from app.api.v1.router import api_router
from app.core.config import settings, validate_production_settings
from app.core.exceptions import BaseRAGInspectorError
from app.core.exceptions import ValidationError as AppValidationError
from app.core.logging import setup_logging
from app.core.rate_limit import limiter
from app.core.http_metrics import HTTPMetricsMiddleware
from app.core.otel import init_otel, instrument_fastapi
from app.core.request_id import REQUEST_ID_HEADER, normalize_request_id
from app.core.security_http import apply_security_headers, cors_middleware_kwargs
from app.core.sentry_init import init_sentry
from app.db.session import Base, engine

setup_logging()
logger = structlog.get_logger()
init_sentry(celery=False)
init_otel(service_name="raginspector-api")

IS_PRODUCTION = settings.ENVIRONMENT.lower() == "production"
ALLOWED_HOSTS = [host.strip() for host in settings.ALLOWED_HOSTS.split(",") if host.strip()]


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting RAGInspector API", environment=settings.ENVIRONMENT)
    validate_production_settings()
    # Auto-create tables only for SQLite local/test DBs. PostgreSQL schema is owned by Alembic —
    # create_all races migrations and can create incompatible ENUM types (e.g. userrole).
    dialect = engine.dialect.name
    if not IS_PRODUCTION and dialect == "sqlite":
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables created/verified", dialect=dialect)
        except Exception as e:
            logger.warning("Database table creation skipped", error=str(e))
    else:
        logger.info(
            "Skipping automatic table creation; run Alembic migrations",
            dialect=dialect,
            environment=settings.ENVIRONMENT,
        )
    yield
    logger.info("Shutting down RAGInspector API")


app = FastAPI(
    title="RAGInspector API",
    description="Production RAG Pipeline Debugger & Observability Platform",
    version="1.0.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(HTTPMetricsMiddleware)
instrument_fastapi(app)


@app.exception_handler(BaseRAGInspectorError)
async def raginspector_error_handler(request: Request, exc: BaseRAGInspectorError):
    """Map domain errors to stable JSON without exposing stack traces."""
    status = 400 if isinstance(exc, AppValidationError) else 422
    if exc.code in {"configuration_error", "database_error", "worker_error"}:
        status = 503
    elif exc.code in {"timeout_error", "network_error", "provider_error"}:
        status = 504 if exc.code == "timeout_error" else 502
    return JSONResponse(
        status_code=status,
        content={"detail": exc.to_dict()},
    )


@app.middleware("http")
async def request_context(request: Request, call_next):
    """Bind request_id / correlation / trace into structlog; echo headers."""
    clear_contextvars()
    request_id = normalize_request_id(request.headers.get(REQUEST_ID_HEADER))
    correlation_id = normalize_request_id(
        request.headers.get("X-Correlation-ID") or request_id
    )
    from app.core.logging import new_error_id, new_trace_id

    trace_id = normalize_request_id(request.headers.get("X-Trace-ID")) or new_trace_id()
    bind_contextvars(
        request_id=request_id,
        correlation_id=correlation_id,
        trace_id=trace_id,
    )
    request.state.request_id = request_id
    request.state.correlation_id = correlation_id
    request.state.trace_id = trace_id
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        error_id = new_error_id()
        bind_contextvars(error_id=error_id)
        logger.exception(
            "request_failed",
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms,
            error_id=error_id,
        )
        clear_contextvars()
        raise
    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers[REQUEST_ID_HEADER] = request_id
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Trace-ID"] = trace_id
    logger.info(
        "request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration_ms,
    )
    clear_contextvars()
    return response


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    return apply_security_headers(response, is_production=IS_PRODUCTION)


# CORS — production locks origins to FRONTEND_URL (no trailing slash) and explicit methods/headers
app.add_middleware(
    CORSMiddleware,
    **cors_middleware_kwargs(
        is_production=IS_PRODUCTION,
        frontend_url=settings.FRONTEND_URL,
    ),
)

if IS_PRODUCTION:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=ALLOWED_HOSTS,
    )

# Include routers
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/live")
async def liveness_check():
    """Kubernetes-style liveness alias for ``/health`` (Phase 8.4)."""
    return await health_check()
