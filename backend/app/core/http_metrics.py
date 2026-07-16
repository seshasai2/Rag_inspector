"""In-process HTTP RED metrics for Prometheus scrapes.

Counters/histograms are process-local (multi-replica scrapes aggregate upstream).
Path labels use the matched route template when available to avoid cardinality explosion.
"""

from __future__ import annotations

import re
import threading
import time
from collections import defaultdict
from typing import DefaultDict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

_lock = threading.Lock()
_request_counts: DefaultDict[tuple[str, str, str], int] = defaultdict(int)
# Bucket upper bounds in seconds (Prometheus-style cumulative histogram).
_DURATION_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
_duration_buckets: DefaultDict[tuple[str, str], DefaultDict[float, int]] = defaultdict(
    lambda: defaultdict(int)
)
_duration_sum: DefaultDict[tuple[str, str], float] = defaultdict(float)
_duration_count: DefaultDict[tuple[str, str], int] = defaultdict(int)

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_HEX_RE = re.compile(r"/[0-9a-fA-F]{24,}/?")


def reset_http_metrics_for_tests() -> None:
    """Clear in-process counters (unit tests only)."""
    with _lock:
        _request_counts.clear()
        _duration_buckets.clear()
        _duration_sum.clear()
        _duration_count.clear()


def _normalize_path(path: str) -> str:
    path = _UUID_RE.sub("{id}", path)
    path = _HEX_RE.sub("/{id}", path)
    if len(path) > 120:
        return path[:120]
    return path or "/"


def record_http_request(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    method_l = (method or "GET").upper()
    path_l = _normalize_path(path)
    status_l = str(status_code)
    key = (method_l, path_l, status_l)
    dur_key = (method_l, path_l)
    with _lock:
        _request_counts[key] += 1
        _duration_sum[dur_key] += duration_seconds
        _duration_count[dur_key] += 1
        for bound in _DURATION_BUCKETS:
            if duration_seconds <= bound:
                _duration_buckets[dur_key][bound] += 1
        _duration_buckets[dur_key][float("inf")] += 1


def render_http_metrics_lines() -> list[str]:
    """Prometheus text exposition lines for HTTP RED metrics."""
    lines: list[str] = [
        "# HELP raginspector_http_requests_total Total HTTP requests by method, path, status",
        "# TYPE raginspector_http_requests_total counter",
    ]
    with _lock:
        counts = dict(_request_counts)
        bucket_snap = {
            k: dict(v) for k, v in _duration_buckets.items()
        }
        sum_snap = dict(_duration_sum)
        count_snap = dict(_duration_count)

    if not counts:
        # Keep scrape healthy even before first request.
        lines.append('raginspector_http_requests_total{method="GET",path="/",status="200"} 0')
    else:
        for (method, path, status), value in sorted(counts.items()):
            lines.append(
                f'raginspector_http_requests_total{{method="{method}",path="{path}",status="{status}"}} {value}'
            )

    lines.extend(
        [
            "# HELP raginspector_http_request_duration_seconds HTTP request latency histogram",
            "# TYPE raginspector_http_request_duration_seconds histogram",
        ]
    )
    for (method, path), buckets in sorted(bucket_snap.items()):
        cumulative = 0
        for bound in _DURATION_BUCKETS:
            cumulative += buckets.get(bound, 0)
            le = f"{bound:g}"
            lines.append(
                f'raginspector_http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="{le}"}} {cumulative}'
            )
        total = count_snap.get((method, path), 0)
        lines.append(
            f'raginspector_http_request_duration_seconds_bucket{{method="{method}",path="{path}",le="+Inf"}} {total}'
        )
        lines.append(
            f'raginspector_http_request_duration_seconds_sum{{method="{method}",path="{path}"}} {sum_snap.get((method, path), 0.0):.6f}'
        )
        lines.append(
            f'raginspector_http_request_duration_seconds_count{{method="{method}",path="{path}"}} {total}'
        )
    return lines


class HTTPMetricsMiddleware(BaseHTTPMiddleware):
    """Record Rate / Errors / Duration for every HTTP request."""

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        started = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            # Prefer route template when available (lower cardinality).
            route = request.scope.get("route")
            path = getattr(route, "path", None) or request.url.path
            duration = time.perf_counter() - started
            record_http_request(request.method, path, status_code, duration)
