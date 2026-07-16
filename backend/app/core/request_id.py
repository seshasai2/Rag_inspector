"""Request ID helpers for structured logging (Phase 8.3)."""

from __future__ import annotations

import re
import uuid

REQUEST_ID_HEADER = "X-Request-ID"
# Allow client-supplied IDs that look like UUIDs or short opaque tokens.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{8,128}$")


def new_request_id() -> str:
    return str(uuid.uuid4())


def normalize_request_id(value: str | None) -> str:
    if value and _SAFE_REQUEST_ID.match(value.strip()):
        return value.strip()
    return new_request_id()
