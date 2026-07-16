"""Optional Redis JSON cache (fail-open).

Used for short-TTL dashboard aggregates. If Redis is down or disabled,
callers always recompute from the database.
"""

from __future__ import annotations

import json
import threading
from typing import Any, Optional

from redis import Redis
from redis.asyncio import Redis as AsyncRedis

from app.core.config import settings

_client: Optional[Redis] = None
_client_lock = threading.Lock()
_client_failed = False

_async_client: Optional[AsyncRedis] = None
_async_client_lock = threading.Lock()
_async_client_failed = False


def reset_redis_cache_for_tests() -> None:
    """Clear process client (unit tests only)."""
    global _client, _client_failed, _async_client, _async_client_failed
    with _client_lock:
        if _client is not None:
            try:
                _client.close()
            except Exception:
                pass
        _client = None
        _client_failed = False
    with _async_client_lock:
        if _async_client is not None:
            try:
                close = getattr(_async_client, "close", None)
                if close is not None:
                    close()
            except Exception:
                pass
        _async_client = None
        _async_client_failed = False


def _get_client() -> Optional[Redis]:
    global _client, _client_failed
    if _client_failed:
        return None
    if _client is not None:
        return _client
    with _client_lock:
        if _client_failed:
            return None
        if _client is not None:
            return _client
        try:
            client = Redis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                decode_responses=True,
            )
            client.ping()
            _client = client
            return _client
        except Exception:
            _client_failed = True
            return None


def _get_async_client() -> Optional[AsyncRedis]:
    global _async_client, _async_client_failed
    if _async_client_failed:
        return None
    if _async_client is not None:
        return _async_client
    with _async_client_lock:
        if _async_client_failed:
            return None
        if _async_client is not None:
            return _async_client
        try:
            client = AsyncRedis.from_url(
                settings.REDIS_URL,
                socket_connect_timeout=settings.REDIS_SOCKET_CONNECT_TIMEOUT,
                socket_timeout=settings.REDIS_SOCKET_TIMEOUT,
                decode_responses=True,
            )
            _async_client = client
            return _async_client
        except Exception:
            _async_client_failed = True
            return None


def cache_get_json(key: str) -> Optional[Any]:
    client = _get_client()
    if client is None:
        return None
    try:
        raw = client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None


def cache_set_json(key: str, value: Any, ttl_seconds: int) -> bool:
    if ttl_seconds <= 0:
        return False
    client = _get_client()
    if client is None:
        return False
    try:
        client.set(key, json.dumps(value, default=str), ex=ttl_seconds)
        return True
    except Exception:
        return False


async def cache_get_json_async(key: str) -> Optional[Any]:
    client = _get_async_client()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception:
        return None


async def cache_set_json_async(key: str, value: Any, ttl_seconds: int) -> bool:
    if ttl_seconds <= 0:
        return False
    client = _get_async_client()
    if client is None:
        return False
    try:
        await client.set(key, json.dumps(value, default=str), ex=ttl_seconds)
        return True
    except Exception:
        return False
