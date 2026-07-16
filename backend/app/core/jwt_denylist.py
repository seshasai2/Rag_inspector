"""Access-token JWT denylist (Redis-backed).

On logout the access-token ``jti`` is stored until the token's natural expiry.
``get_current_user`` rejects denylisted JTIs.

When Redis is unavailable, deny/check fail open (availability over perfect revoke)
and increment ``raginspector_jwt_denylist_failopen_total`` so operators can alert.
The short access TTL (default 15m) bounds residual risk.
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional

from app.core.redis_cache import _get_client

_DENY_PREFIX = "jwt:deny:"
_failopen_lock = threading.Lock()
_failopen_count = 0


def reset_denylist_metrics_for_tests() -> None:
    global _failopen_count
    with _failopen_lock:
        _failopen_count = 0


def _bump_failopen() -> None:
    global _failopen_count
    with _failopen_lock:
        _failopen_count += 1


def denylist_failopen_total() -> int:
    with _failopen_lock:
        return _failopen_count


def deny_access_jti(jti: str, ttl_seconds: int) -> bool:
    """Mark an access-token jti as revoked until ``ttl_seconds`` elapses."""
    if not jti or ttl_seconds <= 0:
        return False
    client = _get_client()
    if client is None:
        _bump_failopen()
        return False
    try:
        client.set(f"{_DENY_PREFIX}{jti}", "1", ex=int(ttl_seconds))
        return True
    except Exception:
        _bump_failopen()
        return False


def is_access_jti_denied(jti: str) -> bool:
    """Return True if ``jti`` is on the denylist. Fail-open when Redis is down."""
    if not jti:
        return False
    client = _get_client()
    if client is None:
        _bump_failopen()
        return False
    try:
        return bool(client.get(f"{_DENY_PREFIX}{jti}"))
    except Exception:
        _bump_failopen()
        return False


def remaining_ttl_seconds(exp: Optional[int | float]) -> int:
    """Seconds until JWT ``exp`` (unix timestamp). Zero if already expired."""
    if exp is None:
        return 0
    now = datetime.now(timezone.utc).timestamp()
    return max(0, int(float(exp) - now))


def render_denylist_metrics_lines() -> list[str]:
    return [
        "# HELP raginspector_jwt_denylist_failopen_total Times denylist ops failed open (Redis unavailable)",
        "# TYPE raginspector_jwt_denylist_failopen_total counter",
        f"raginspector_jwt_denylist_failopen_total {denylist_failopen_total()}",
    ]
