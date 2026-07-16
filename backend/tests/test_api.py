"""
Integration tests for RAGInspector API.

Run (SQLite / Windows):
  pytest tests/test_api.py -q

Run (Postgres / CI):
  TESTING=1 TEST_DATABASE_URL=postgresql+asyncpg://... pytest tests/test_api.py -q
"""
from __future__ import annotations

import os
import sys
import uuid

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Ensure test mode before app imports pull in rate limiter / settings side effects.
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("ENVIRONMENT", "test")

from app.core.config import settings  # noqa: E402
from app.db.session import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


def _resolve_test_database_url() -> str:
    explicit = os.getenv("TEST_DATABASE_URL")
    if explicit:
        return explicit

    if sys.platform == "win32":
        return "sqlite+aiosqlite:///./raginspector_test_current.db"

    db_url = make_url(settings.DATABASE_URL)
    if db_url.drivername.startswith("sqlite"):
        database = db_url.database or "./raginspector.db"
        if database.endswith("raginspector.db"):
            database = database.replace("raginspector.db", "raginspector_test.db")
        else:
            database = f"{database}_test"
        return str(db_url.set(database=database))

    if db_url.drivername.startswith("postgresql"):
        # Change only the DB name — never mangle user/password via str.replace.
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
    async with test_engine.begin() as conn:
        url = make_url(TEST_DB_URL)
        if url.drivername.startswith("postgresql"):
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    email = f"test+{uuid.uuid4().hex}@example.com"
    password = "TestPassword1"
    reg = await client.post(
        "/api/v1/auth/register",
        json={"name": "Test User", "email": email, "password": password},
    )
    assert reg.status_code == 201, reg.text
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, resp.text
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


class TestAuth:
    async def test_register(self, client: AsyncClient):
        email = f"new+{uuid.uuid4().hex}@example.com"
        resp = await client.post(
            "/api/v1/auth/register",
            json={"name": "New User", "email": email, "password": "NewPassword1"},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == email.lower()
        assert "id" in data

    async def test_register_duplicate_email(self, client: AsyncClient):
        email = f"dup+{uuid.uuid4().hex}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={"name": "Dup User", "email": email, "password": "DupPassword1"},
        )
        resp = await client.post(
            "/api/v1/auth/register",
            json={"name": "Dup User 2", "email": email, "password": "DupPassword1"},
        )
        assert resp.status_code == 400

    async def test_login_success(self, client: AsyncClient):
        email = f"login+{uuid.uuid4().hex}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={"name": "Login User", "email": email, "password": "LoginPass1"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "LoginPass1"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data

    async def test_login_wrong_password(self, client: AsyncClient):
        email = f"wrong+{uuid.uuid4().hex}@example.com"
        await client.post(
            "/api/v1/auth/register",
            json={"name": "Wrong User", "email": email, "password": "RightPass1"},
        )
        resp = await client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": "WrongPass1"},
        )
        assert resp.status_code == 401

    async def test_me_authenticated(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"].endswith("@example.com")
        assert resp.json()["email"].startswith("test+")

    async def test_me_unauthenticated(self, client: AsyncClient):
        resp = await client.get("/api/v1/auth/me")
        assert resp.status_code == 401


class TestPipelines:
    async def test_create_pipeline(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post(
            "/api/v1/pipelines",
            headers=auth_headers,
            json={"name": "test-pipeline", "description": "Test pipeline"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"] == "test-pipeline"

    async def test_list_pipelines(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/pipelines", headers=auth_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    async def test_get_pipeline_not_found(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            "/api/v1/pipelines/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert resp.status_code == 404


class TestAPIKeys:
    async def test_create_and_list_keys(self, client: AsyncClient, auth_headers: dict):
        resp = await client.post("/api/v1/keys", headers=auth_headers, json={"name": "test-key"})
        assert resp.status_code == 201
        data = resp.json()
        assert "raw_key" in data
        assert data["raw_key"].startswith("ri-")

        list_resp = await client.get("/api/v1/keys", headers=auth_headers)
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

    async def test_revoke_key(self, client: AsyncClient, auth_headers: dict):
        create_resp = await client.post(
            "/api/v1/keys", headers=auth_headers, json={"name": "to-revoke"}
        )
        key_id = create_resp.json()["id"]
        del_resp = await client.delete(f"/api/v1/keys/{key_id}", headers=auth_headers)
        assert del_resp.status_code == 204


class TestIngest:
    async def test_ingest_requires_api_key(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/ingest/trace",
            json={"pipeline_name": "test", "query_text": "hello"},
        )
        assert resp.status_code == 401

    async def test_ingest_trace(self, client: AsyncClient, auth_headers: dict):
        key_resp = await client.post(
            "/api/v1/keys", headers=auth_headers, json={"name": "ingest-test"}
        )
        raw_key = key_resp.json()["raw_key"]

        resp = await client.post(
            "/api/v1/ingest/trace",
            headers={"X-API-Key": raw_key},
            json={
                "pipeline_name": "test-pipeline",
                "query_text": "What is the capital of France?",
                "answer_text": "The capital of France is Paris.",
                "retrieved_chunks": [
                    {
                        "chunk_id": "chunk_1",
                        "chunk_text": "Paris is the capital and largest city of France.",
                        "similarity_score": 0.92,
                        "rank": 1,
                    }
                ],
                "retrieve_latency_ms": 45.2,
                "generate_latency_ms": 320.5,
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        # Celery may be unavailable in CI — both accepted statuses are valid.
        assert data["status"] in {"accepted", "accepted_unanalyzed"}
        assert "trace_id" in data


class TestQueries:
    async def test_list_queries(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/queries", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_list_queries_with_filter(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            "/api/v1/queries?failure_type=hallucination", headers=auth_headers
        )
        assert resp.status_code == 200


class TestMetrics:
    async def test_dashboard_metrics(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/metrics/dashboard", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total_queries" in data
        assert "hallucination_rate" in data
        assert "trustworthiness_score" in data

    async def test_timeseries(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            "/api/v1/metrics/timeseries?metric=faithfulness_score&days=7",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        assert "data" in resp.json()

    async def test_failure_distribution(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get(
            "/api/v1/metrics/failure-distribution", headers=auth_headers
        )
        assert resp.status_code == 200


class TestSettings:
    async def test_get_settings(self, client: AsyncClient, auth_headers: dict):
        resp = await client.get("/api/v1/settings", headers=auth_headers)
        assert resp.status_code == 200
        assert "ollama_url" in resp.json()

    async def test_update_settings(self, client: AsyncClient, auth_headers: dict):
        resp = await client.put(
            "/api/v1/settings",
            headers=auth_headers,
            json={
                "grounding_threshold": 0.6,
                "faithfulness_alert_threshold": 0.75,
            },
        )
        assert resp.status_code == 200
        assert resp.json()["grounding_threshold"] == 0.6


class TestHealth:
    async def test_health(self, client: AsyncClient):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"
