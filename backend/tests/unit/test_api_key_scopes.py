"""API key scope parsing — exact grant, not substring (Phase 5.6)."""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.api import deps
from app.core.api_scopes import api_key_allows_scope, parse_api_key_scopes


def test_parse_json_scopes():
    assert parse_api_key_scopes(json.dumps(["ingest:write", "metrics:read"])) == [
        "ingest:write",
        "metrics:read",
    ]


def test_parse_legacy_comma_scopes():
    assert parse_api_key_scopes("ingest:write, metrics:read") == [
        "ingest:write",
        "metrics:read",
    ]


def test_parse_invalid_or_empty():
    assert parse_api_key_scopes(None) == []
    assert parse_api_key_scopes("") == []
    assert parse_api_key_scopes("{not-json}") == []
    assert parse_api_key_scopes('{"a": 1}') == []


def test_substring_false_positive_blocked():
    """Old bug: 'read' in '["metrics:read"]' via substring — must not grant."""
    stored = json.dumps(["metrics:read"])
    assert api_key_allows_scope(stored, "metrics:read") is True
    assert api_key_allows_scope(stored, "read") is False
    assert api_key_allows_scope(stored, "metrics") is False
    assert api_key_allows_scope(stored, "ingest:write") is False


def test_ingest_substring_of_ingest_write_blocked():
    stored = json.dumps(["ingest:write"])
    assert api_key_allows_scope(stored, "ingest:write") is True
    assert api_key_allows_scope(stored, "ingest") is False
    assert api_key_allows_scope(stored, "write") is False


def test_wildcard_grants_all():
    stored = json.dumps(["*"])
    assert api_key_allows_scope(stored, "ingest:write") is True
    assert api_key_allows_scope(stored, "metrics:read") is True


@pytest.mark.asyncio
async def test_require_api_scope_rejects_substring_match():
    """Integration-style: checker must 403 when only a substring would match."""
    user = MagicMock()
    key = MagicMock()
    key.scopes = json.dumps(["metrics:read"])

    result = MagicMock()
    result.scalar_one_or_none.return_value = key
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    checker = deps.require_api_scope("ingest:write")
    with (
        patch.object(deps, "get_user_from_api_key", AsyncMock(return_value=user)),
        patch.object(deps, "hash_api_key", return_value="hash"),
    ):
        with pytest.raises(HTTPException) as exc:
            await checker(api_key="ri-test", db=db)
    assert exc.value.status_code == 403
    assert exc.value.detail == "API key scope not permitted"


@pytest.mark.asyncio
async def test_require_api_scope_allows_exact_json_scope():
    user = MagicMock()
    key = MagicMock()
    key.scopes = json.dumps(["ingest:write", "metrics:read"])

    result = MagicMock()
    result.scalar_one_or_none.return_value = key
    db = MagicMock()
    db.execute = AsyncMock(return_value=result)

    checker = deps.require_api_scope("ingest:write")
    with (
        patch.object(deps, "get_user_from_api_key", AsyncMock(return_value=user)),
        patch.object(deps, "hash_api_key", return_value="hash"),
    ):
        assert await checker(api_key="ri-test", db=db) is user
