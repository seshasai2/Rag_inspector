import os
import ssl
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import structlog
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

logger = structlog.get_logger()


class Base(DeclarativeBase):
    pass


def should_use_sqlite() -> bool:
    """Decide whether to use SQLite instead of PostgreSQL.

    Priority:
    1. FORCE_POSTGRES=1 → always Postgres (CI / Docker).
    2. DATABASE_URL starts with sqlite → SQLite.
    3. DATABASE_URL is postgresql* → Postgres when asyncpg is installed;
       otherwise SQLite fallback for local Windows without drivers
       (unless FORCE_POSTGRES is set).
    4. Otherwise → SQLite.
    """
    if os.environ.get("FORCE_POSTGRES", "").lower() in {"1", "true", "yes"}:
        return False
    url = settings.DATABASE_URL.lower()
    if url.startswith("sqlite"):
        return True
    if url.startswith("postgresql"):
        try:
            import asyncpg  # noqa: F401

            return False
        except ImportError:
            logger.warning(
                "PostgreSQL URL configured but asyncpg not installed; "
                "falling back to SQLite. Install asyncpg or set FORCE_POSTGRES=1 with drivers."
            )
            return True
    return True


def _strip_asyncpg_incompatible_query(url: str) -> str:
    """Remove libpq query params that SQLAlchemy forwards as asyncpg kwargs (TypeError)."""
    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    for key in (
        "ssl",
        "sslmode",
        "sslrootcert",
        "sslcert",
        "sslkey",
        "channel_binding",
        "gssencmode",
    ):
        query.pop(key, None)
    return urlunparse(parsed._replace(query=urlencode(query)))


def _needs_tls(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    if host in {"localhost", "127.0.0.1", "db", "postgres"}:
        return False
    return True


if should_use_sqlite():
    sqlite_async_url = "sqlite+aiosqlite:///./raginspector.db"
    sqlite_sync_url = "sqlite:///./raginspector.db"

    engine = create_async_engine(
        sqlite_async_url,
        echo=settings.ENVIRONMENT == "development",
        connect_args={"check_same_thread": False},
    )

    sync_engine = create_engine(
        sqlite_sync_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    async_url = _strip_asyncpg_incompatible_query(settings.DATABASE_URL)
    async_connect_args: dict = {}
    if _needs_tls(async_url):
        # Neon / Render External: pass SSL via connect_args (not URL query).
        async_connect_args["ssl"] = ssl.create_default_context()

    engine = create_async_engine(
        async_url,
        echo=settings.ENVIRONMENT == "development",
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        connect_args=async_connect_args,
    )

    sync_engine = create_engine(
        settings.DATABASE_SYNC_URL,
        echo=False,
        pool_pre_ping=True,
    )

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
