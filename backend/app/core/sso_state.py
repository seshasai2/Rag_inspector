"""OAuth CSRF state — HMAC-signed, redis-optional one-time nonce blacklist."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from typing import Optional
from urllib.parse import quote, unquote

from app.core.config import settings
from app.core.redis_cache import cache_get_json, cache_set_json

_SSO_STATE_TTL = 600
_USED_PREFIX = "sso:oauth_used:"


def _sign(payload: str) -> str:
    digest = hmac.new(
        settings.SECRET_KEY.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return digest


def mint_oauth_state(provider: str) -> str:
    nonce = secrets.token_urlsafe(16)
    issued = int(time.time())
    payload = f"{provider}:{nonce}:{issued}"
    state = f"{quote(payload, safe='')}.{_sign(payload)}"
    return state


def consume_oauth_state(state: Optional[str], *, expected_provider: str) -> bool:
    if not state or "." not in state:
        return False
    payload_enc, signature = state.rsplit(".", 1)
    try:
        payload = unquote(payload_enc)
    except Exception:
        return False
    if not hmac.compare_digest(_sign(payload), signature):
        return False
    try:
        provider, nonce, issued_s = payload.split(":", 2)
        issued = int(issued_s)
    except ValueError:
        return False
    if provider != expected_provider:
        return False
    if abs(int(time.time()) - issued) > _SSO_STATE_TTL:
        return False
    used_key = f"{_USED_PREFIX}{nonce}"
    if cache_get_json(used_key):
        return False
    cache_set_json(used_key, {"used": True}, ttl_seconds=_SSO_STATE_TTL)
    return True
