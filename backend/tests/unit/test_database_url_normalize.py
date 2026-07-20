"""Managed Postgres URL normalization for free-cloud hosts."""

from app.core.config import normalize_database_urls


def test_render_style_url_gets_asyncpg_and_ssl_in_production():
    async_url, sync_url = normalize_database_urls(
        "postgresql://u:p@dpg-abc.oregon-postgres.render.com/raginspector",
        "postgresql://u:p@dpg-abc.oregon-postgres.render.com/raginspector",
        environment="production",
    )
    assert async_url.startswith("postgresql+asyncpg://")
    assert "ssl=require" in async_url
    assert sync_url.startswith("postgresql://")
    assert "sslmode=require" in sync_url
    assert "+asyncpg" not in sync_url


def test_postgres_scheme_alias():
    async_url, sync_url = normalize_database_urls(
        "postgres://u:p@db.example.com/x",
        "postgres://u:p@db.example.com/x",
        environment="production",
    )
    assert async_url.startswith("postgresql+asyncpg://")
    assert sync_url.startswith("postgresql://")


def test_render_external_url_gets_ssl_even_in_development():
    async_url, sync_url = normalize_database_urls(
        "postgresql://u:p@dpg-abc-a.oregon-postgres.render.com/raginspector",
        "postgresql://u:p@dpg-abc-a.oregon-postgres.render.com/raginspector",
        environment="development",
    )
    assert "ssl=require" in async_url
    assert "sslmode=require" in sync_url


def test_compose_service_hostname_skips_ssl_in_production():
    async_url, _ = normalize_database_urls(
        "postgresql://u:strong@db:5432/raginspector",
        "postgresql://u:strong@db:5432/raginspector",
        environment="production",
    )
    assert "ssl=" not in async_url
