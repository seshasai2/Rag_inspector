"""API key scope parsing — scopes are stored as JSON lists, never matched as substrings."""

from __future__ import annotations

import json
from typing import Iterable


def parse_api_key_scopes(raw: str | None) -> list[str]:
    """Parse stored API key scopes into a list of exact scope strings.

    Canonical storage is ``json.dumps(["ingest:write", ...])``.
    Also accepts a comma-separated legacy string for older rows.
    """
    if raw is None:
        return []
    text = raw.strip()
    if not text:
        return []

    # Prefer JSON (canonical). Objects / invalid JSON that look like JSON → deny.
    if text[0] in "[{":
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            return []
        if not isinstance(data, list):
            return []
        return [str(item).strip() for item in data if str(item).strip()]

    # Legacy: comma-separated scopes
    return [part.strip() for part in text.split(",") if part.strip()]


def api_key_allows_scope(stored_scopes: str | None, required: str) -> bool:
    """True iff ``required`` is an exact granted scope (or wildcard ``*``)."""
    granted = parse_api_key_scopes(stored_scopes)
    if "*" in granted:
        return True
    return required in granted


def scopes_as_json(scopes: Iterable[str]) -> str:
    return json.dumps(list(scopes))
