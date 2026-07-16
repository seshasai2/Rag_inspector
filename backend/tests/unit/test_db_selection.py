"""Tests for DB engine selection helpers."""
import sys

from app.db import session as session_mod


def test_force_postgres_disables_sqlite(monkeypatch):
    monkeypatch.setenv("FORCE_POSTGRES", "1")
    monkeypatch.setattr(session_mod.settings, "DATABASE_URL", "postgresql+asyncpg://x")
    assert session_mod.should_use_sqlite() is False


def test_explicit_sqlite_url(monkeypatch):
    monkeypatch.delenv("FORCE_POSTGRES", raising=False)
    monkeypatch.setattr(session_mod.settings, "DATABASE_URL", "sqlite+aiosqlite:///./tmp.db")
    assert session_mod.should_use_sqlite() is True


def test_postgres_url_uses_sqlite_without_asyncpg(monkeypatch):
    monkeypatch.delenv("FORCE_POSTGRES", raising=False)
    monkeypatch.setattr(session_mod.settings, "DATABASE_URL", "postgresql+asyncpg://localhost/db")
    monkeypatch.setitem(sys.modules, "asyncpg", None)
    # Simulate ImportError by removing asyncpg if present and patching import
    import builtins
    real_import = builtins.__import__

    def fake_import(name, *args, **kwargs):
        if name == "asyncpg":
            raise ImportError("simulated")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    assert session_mod.should_use_sqlite() is True
