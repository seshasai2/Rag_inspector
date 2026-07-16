"""Shared fixtures for backend integration tests (ASGI + SQLite/Postgres)."""
from __future__ import annotations

import os
import sys
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Must run before app imports pull in rate limiter / settings side effects.
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("REQUIRE_EMAIL_VERIFICATION", "false")

from app.core.config import settings  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


def _resolve_test_database_url() -> str:
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return explicit

    if sys.platform == "win32":
        return "sqlite+aiosqlite:///./raginspector_integration_test.db"

    db_url = make_url(settings.DATABASE_URL)
    if db_url.drivername.startswith("sqlite"):
        database = db_url.database or "./raginspector.db"
        if database.endswith("raginspector.db"):
            database = database.replace("raginspector.db", "raginspector_integration_test.db")
        else:
            database = f"{database}_integration"
        return str(db_url.set(database=database))

    if db_url.drivername.startswith("postgresql"):
        return str(db_url.set(database="raginspector_test"))

    return settings.DATABASE_URL


TEST_DB_URL = _resolve_test_database_url()
_connect_args = {"check_same_thread": False} if TEST_DB_URL.startswith("sqlite") else {}
test_engine = create_async_engine(TEST_DB_URL, echo=False, connect_args=_connect_args)
TestSessionLocal = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    try:
        async with test_engine.begin() as conn:
            url = make_url(TEST_DB_URL)
            if url.drivername.startswith("postgresql"):
                await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
    except Exception as exc:  # pragma: no cover - environment dependent
        pytest.skip(f"Integration DB unavailable: {exc}")
    yield
    try:
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
    finally:
        await test_engine.dispose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    email = f"integ+{uuid.uuid4().hex}@example.com"
    password = "IntegPass123!"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Integration User", "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {
        "Authorization": f"Bearer {token}",
        "email": email,
        "password": password,
        "refresh_token": resp.json()["refresh_token"],
    }


def _redis_ping() -> bool:
    """Return True when settings.REDIS_URL answers PING."""
    try:
        from redis import Redis

        client = Redis.from_url(
            settings.REDIS_URL,
            socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
            socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
        )
        try:
            return bool(client.ping())
        finally:
            client.close()
    except Exception:
        return False


@pytest.fixture
def redis_available() -> bool:
    return _redis_ping()
