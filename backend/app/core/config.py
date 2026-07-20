"""
RAGInspector configuration.
"""

from typing import Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_urls(
    database_url: str,
    database_sync_url: str,
    *,
    environment: str = "development",
) -> tuple[str, str]:
    """Normalize managed-Postgres URLs for async SQLAlchemy + sync Alembic/Celery.

    Cloud providers (Render, Railway, Neon, …) typically inject ``postgresql://``
    (or ``postgres://``) without the asyncpg driver prefix. Managed hosts usually
    require TLS.

    Important: asyncpg (via SQLAlchemy) rejects libpq ``sslmode=`` query kwargs
    (``TypeError``). We strip those from the async URL and use ``ssl=true`` instead.
    Sync URLs keep ``sslmode=require`` for psycopg/libpq.
    """

    def _strip_driver(url: str) -> str:
        for prefix in (
            "postgresql+asyncpg://",
            "postgresql+psycopg2://",
            "postgresql+psycopg://",
            "postgres://",
            "postgresql://",
        ):
            if url.startswith(prefix):
                return "postgresql://" + url[len(prefix) :]
        return url

    def _with_query(url: str, *, drop: set[str] | None = None, **params: str) -> str:
        parsed = urlparse(url)
        query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        for key in drop or ():
            query.pop(key, None)
        for key, value in params.items():
            query[key] = value
        return urlunparse(parsed._replace(query=urlencode(query)))

    def _needs_cloud_ssl(url: str) -> bool:
        host = (urlparse(url).hostname or "").lower()
        if host in {"localhost", "127.0.0.1", "db", "postgres"}:
            return False
        if environment.lower() == "production":
            return True
        cloud_markers = (
            ".render.com",
            ".neon.tech",
            ".supabase.co",
            ".amazonaws.com",
            ".railway.app",
            ".upstash.io",
            ".aivencloud.com",
        )
        return any(host.endswith(m) for m in cloud_markers) or host.startswith("dpg-")

    base_async = _strip_driver(database_url)
    base_sync = _strip_driver(database_sync_url or database_url)

    # Always drop libpq-only params from the async URL — asyncpg TypeErrors on them.
    _async_drop = {
        "sslmode",
        "sslrootcert",
        "sslcert",
        "sslkey",
        "channel_binding",
        "gssencmode",
    }
    base_async = _with_query(base_async, drop=_async_drop)

    if _needs_cloud_ssl(base_async):
        # asyncpg: use ssl=true (not sslmode)
        base_async = _with_query(base_async, drop=_async_drop, ssl="true")
    if _needs_cloud_ssl(base_sync):
        base_sync = _with_query(
            base_sync,
            drop={"ssl", "channel_binding"},
            sslmode="require",
        )

    async_url = "postgresql+asyncpg://" + base_async[len("postgresql://") :]
    sync_url = base_sync
    return async_url, sync_url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore",
    )

    # Database
    DATABASE_URL: str = (
        "postgresql+asyncpg://raginspector:raginspector_secret@localhost:5432/raginspector"
    )
    DATABASE_SYNC_URL: str = (
        "postgresql://raginspector:raginspector_secret@localhost:5432/raginspector"
    )

    # Redis
    REDIS_URL: str = "redis://:redis_secret@localhost:6379/0"
    REDIS_SOCKET_CONNECT_TIMEOUT: float = 0.5
    REDIS_SOCKET_TIMEOUT: float = 0.5
    # Optional short-TTL cache for /metrics/dashboard (+ related aggregates)
    DASHBOARD_METRICS_CACHE_ENABLED: bool = True
    DASHBOARD_METRICS_CACHE_TTL_SECONDS: int = 30

    # Analysis worker Celery time limits
    ANALYSIS_SOFT_TIME_LIMIT_SECONDS: int = 600
    ANALYSIS_HARD_TIME_LIMIT_SECONDS: int = 720

    # JWT
    SECRET_KEY: str = "supersecretkey_change_in_production_min_32_chars"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Hugging Face Inference API (free replacement for Ollama)
    HF_API_TOKEN: Optional[str] = None
    HF_MODEL: str = "HuggingFaceH4/zephyr-7b-beta"
    # Fallback to Ollama if HF token is not set
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.2:3b"

    # Razorpay
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None
    # PRD v2.0 pricing — each plan shows both INR and USD
    RAZORPAY_PLAN_STARTER_MONTHLY: Optional[str] = None
    RAZORPAY_PLAN_STARTER_ANNUAL: Optional[str] = None
    RAZORPAY_PLAN_PRO_MONTHLY: Optional[str] = None
    RAZORPAY_PLAN_PRO_ANNUAL: Optional[str] = None
    RAZORPAY_PLAN_ENTERPRISE_MONTHLY: Optional[str] = None
    RAZORPAY_PLAN_ENTERPRISE_ANNUAL: Optional[str] = None

    # Frontend
    FRONTEND_URL: str = "http://localhost:3000"
    # Email — Resend (free, API-based, 3000 emails/mo)
    RESEND_API_KEY: Optional[str] = None
    # SMTP fallback (Gmail, SendGrid, etc.)
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: str = "noreply@raginspector.com"

    # App
    ENVIRONMENT: str = "development"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    SENTRY_DSN: Optional[str] = None
    SUPPORT_ADMIN_EMAILS: str = ""
    # When None: enforce only in production. Set true/false explicitly to override.
    REQUIRE_EMAIL_VERIFICATION: Optional[bool] = None

    # ML models (analysis worker) — see docs/COLD_START.md
    EMBEDDING_MODEL_NAME: str = "all-MiniLM-L6-v2"
    NLI_MODEL_NAME: str = "cross-encoder/nli-deberta-v3-small"
    # Preload NLI + embeddings when each Celery worker process starts
    WARM_ML_MODELS_ON_WORKER_START: bool = True

    # Hybrid merge weights used during analysis BM25 observability stage
    HYBRID_VECTOR_WEIGHT: float = 0.5
    HYBRID_BM25_WEIGHT: float = 0.5

    # Optional shared secret for /api/v1/ops/backlog|experimental (X-Ops-Token)
    OPS_SHARED_TOKEN: Optional[str] = None
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_RETENTION_DAYS: int = 30

    # Optional Google SSO (Phase 10.13)
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = None
    GOOGLE_OAUTH_CLIENT_SECRET: Optional[str] = None
    GOOGLE_OAUTH_REDIRECT_URI: Optional[str] = (
        None  # e.g. http://localhost:8000/api/v1/identity/sso/google/callback
    )

    # Subscription limits (PRD v2.0)
    FREE_TRACES_PER_MONTH: int = 100  # Was 500, now 100
    STARTER_TRACES_PER_MONTH: int = 10000
    PRO_TRACES_PER_MONTH: int = 100000
    ENTERPRISE_TRACES_PER_MONTH: int = 999999999

    @model_validator(mode="after")
    def _normalize_database_urls(self) -> "Settings":
        async_url, sync_url = normalize_database_urls(
            self.DATABASE_URL,
            self.DATABASE_SYNC_URL,
            environment=self.ENVIRONMENT,
        )
        object.__setattr__(self, "DATABASE_URL", async_url)
        object.__setattr__(self, "DATABASE_SYNC_URL", sync_url)
        return self

    @model_validator(mode="after")
    def _resolve_email_verification_gate(self) -> "Settings":
        if self.REQUIRE_EMAIL_VERIFICATION is None:
            object.__setattr__(
                self,
                "REQUIRE_EMAIL_VERIFICATION",
                self.ENVIRONMENT.lower() == "production",
            )
        return self

    def email_verification_required(self) -> bool:
        return bool(self.REQUIRE_EMAIL_VERIFICATION)


settings = Settings()


def validate_production_settings(
    *,
    environment: str | None = None,
    secret_key: str | None = None,
    frontend_url: str | None = None,
    allowed_hosts: str | None = None,
    database_url: str | None = None,
    redis_url: str | None = None,
    ops_shared_token: str | None = None,
) -> None:
    """Fail closed when ``ENVIRONMENT=production`` and config is unsafe (Phase 8.7)."""
    env = (environment if environment is not None else settings.ENVIRONMENT).lower()
    if env != "production":
        return

    secret = secret_key if secret_key is not None else settings.SECRET_KEY
    frontend = frontend_url if frontend_url is not None else settings.FRONTEND_URL
    hosts_raw = allowed_hosts if allowed_hosts is not None else settings.ALLOWED_HOSTS
    db_url = database_url if database_url is not None else settings.DATABASE_URL
    redis = redis_url if redis_url is not None else settings.REDIS_URL
    ops_token = (
        ops_shared_token if ops_shared_token is not None else (settings.OPS_SHARED_TOKEN or "")
    )
    hosts = [h.strip() for h in hosts_raw.split(",") if h.strip()]

    problems: list[str] = []
    if (
        not secret
        or secret == "supersecretkey_change_in_production_min_32_chars"
        or len(secret) < 32
    ):
        problems.append("SECRET_KEY must be a strong production secret")
    if not frontend.startswith("https://"):
        problems.append("FRONTEND_URL must use https in production")
    if not hosts or any(h in {"localhost", "127.0.0.1"} for h in hosts):
        problems.append("ALLOWED_HOSTS must contain production hostnames only")
    if "localhost" in db_url or db_url.startswith("sqlite"):
        problems.append("DATABASE_URL must point to the production database")
    if "raginspector_secret" in db_url:
        problems.append("DATABASE_URL must not use the default development password")
    if "localhost" in redis or "redis_secret" in redis:
        problems.append("REDIS_URL must use a production Redis endpoint and password")
    if not ops_token.strip() or len(ops_token.strip()) < 16:
        problems.append("OPS_SHARED_TOKEN must be a strong secret (≥16 chars) in production")
    if problems:
        raise RuntimeError("Invalid production configuration: " + "; ".join(problems))
