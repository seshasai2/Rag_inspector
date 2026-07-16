"""Shared pytest bootstrap for backend tests."""
from __future__ import annotations

import os

# Must run before app.core.rate_limit (and SlowAPI-decorated endpoints) import.
os.environ.setdefault("TESTING", "1")
os.environ.setdefault("ENVIRONMENT", "test")

from starlette.requests import Request


def make_http_request(path: str = "/api/v1/test", method: str = "POST") -> Request:
    """Build a real Starlette Request for calling rate-limited endpoint functions."""
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": method,
            "scheme": "http",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": [],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }
    )
