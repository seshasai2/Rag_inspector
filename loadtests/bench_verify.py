#!/usr/bin/env python3
"""Evidence-based latency / auth benchmark harness for RAGInspector.

Does not invent success. Writes JSON + markdown-friendly stdout.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import statistics
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import httpx

DEMO_EMAIL = os.environ.get("DEMO_EMAIL", "demo@example.com")
DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "DemoPass123!")


@dataclass
class Sample:
    ok: bool
    ms: float
    status: Optional[int] = None
    error: Optional[str] = None
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


def pct(sorted_vals: list[float], p: float) -> Optional[float]:
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    k = (len(sorted_vals) - 1) * p
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_vals[int(k)]
    return sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)


def summarize(samples: list[Sample]) -> dict[str, Any]:
    oks = [s.ms for s in samples if s.ok]
    fails = [s for s in samples if not s.ok]
    oks_sorted = sorted(oks)
    out: dict[str, Any] = {
        "n": len(samples),
        "ok": len(oks),
        "fail": len(fails),
        "error_rate": (len(fails) / len(samples)) if samples else None,
        "fail_errors": {},
    }
    for s in fails:
        key = s.error or f"status_{s.status}"
        out["fail_errors"][key] = out["fail_errors"].get(key, 0) + 1
    if oks_sorted:
        out.update(
            {
                "min_ms": min(oks_sorted),
                "max_ms": max(oks_sorted),
                "avg_ms": statistics.fmean(oks_sorted),
                "stdev_ms": statistics.pstdev(oks_sorted) if len(oks_sorted) > 1 else 0.0,
                "p50_ms": pct(oks_sorted, 0.50),
                "p75_ms": pct(oks_sorted, 0.75),
                "p90_ms": pct(oks_sorted, 0.90),
                "p95_ms": pct(oks_sorted, 0.95),
                "p99_ms": pct(oks_sorted, 0.99),
            }
        )
    else:
        out["note"] = "NO_SUCCESSFUL_SAMPLES"
    return out


def timed_request(
    client: httpx.Client,
    method: str,
    url: str,
    **kwargs: Any,
) -> Sample:
    t0 = time.perf_counter()
    try:
        r = client.request(method, url, **kwargs)
        ms = (time.perf_counter() - t0) * 1000
        ok = 200 <= r.status_code < 400
        return Sample(
            ok=ok,
            ms=ms,
            status=r.status_code,
            error=None if ok else f"http_{r.status_code}",
        )
    except Exception as exc:  # noqa: BLE001 — capture transport for RCA
        ms = (time.perf_counter() - t0) * 1000
        return Sample(ok=False, ms=ms, status=None, error=type(exc).__name__ + ": " + str(exc)[:200])


def login(client: httpx.Client, api: str) -> tuple[Optional[str], Sample]:
    t0 = time.perf_counter()
    try:
        r = client.post(
            f"{api}/api/v1/auth/login",
            json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
            timeout=30.0,
        )
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code >= 400:
            return None, Sample(ok=False, ms=ms, status=r.status_code, error=f"http_{r.status_code}")
        token = r.json().get("access_token")
        if not token:
            return None, Sample(ok=False, ms=ms, status=r.status_code, error="missing_access_token")
        return token, Sample(ok=True, ms=ms, status=r.status_code)
    except Exception as exc:  # noqa: BLE001
        ms = (time.perf_counter() - t0) * 1000
        return None, Sample(
            ok=False, ms=ms, status=None, error=type(exc).__name__ + ": " + str(exc)[:200]
        )


def reproduce_login_failures(api: str, runs: int, attempts_per_run: int) -> dict[str, Any]:
    """Phase 1: independent runs of login attempts from host → published port."""
    runs_out = []
    for run_i in range(1, runs + 1):
        run_started = datetime.now(timezone.utc).isoformat()
        samples: list[Sample] = []
        with httpx.Client(timeout=30.0) as client:
            for _ in range(attempts_per_run):
                samples.append(
                    timed_request(
                        client,
                        "POST",
                        f"{api}/api/v1/auth/login",
                        json={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
                    )
                )
                time.sleep(0.05)
        summary = summarize(samples)
        runs_out.append(
            {
                "run": run_i,
                "started_at": run_started,
                "ended_at": datetime.now(timezone.utc).isoformat(),
                "summary": summary,
                "first_error": next((s.error for s in samples if not s.ok), None),
                "first_ok_index": next((i for i, s in enumerate(samples) if s.ok), None),
            }
        )
        print(
            f"[reproduce] run={run_i} ok={summary['ok']}/{summary['n']} "
            f"error_rate={summary['error_rate']:.3f} first_error={runs_out[-1]['first_error']}",
            flush=True,
        )
        time.sleep(0.5)
    resetish = sum(
        1
        for r in runs_out
        if r["first_error"]
        and ("ConnectionReset" in r["first_error"] or "RemoteProtocol" in r["first_error"] or "ReadError" in r["first_error"] or "ConnectError" in r["first_error"] or "Timeout" in r["first_error"])
    )
    return {
        "api": api,
        "runs": runs_out,
        "runs_with_transport_failure": resetish,
        "all_runs_had_transport_failure": resetish == runs,
        "any_transport_failure": resetish > 0,
    }


def bench_endpoint(
    client: httpx.Client,
    name: str,
    method: str,
    url: str,
    n: int,
    headers: Optional[dict[str, str]] = None,
    json_body: Any = None,
) -> dict[str, Any]:
    samples = []
    for _ in range(n):
        kwargs: dict[str, Any] = {}
        if headers:
            kwargs["headers"] = headers
        if json_body is not None:
            kwargs["json"] = json_body
        samples.append(timed_request(client, method, url, **kwargs))
    return {"name": name, "url": url, "method": method, "summary": summarize(samples)}


def concurrent_load(
    api: str,
    path: str,
    users: int,
    requests_per_user: int,
    headers_factory: Optional[Callable[[], dict[str, str]]] = None,
) -> dict[str, Any]:
    samples: list[Sample] = []

    def worker(_: int) -> list[Sample]:
        out: list[Sample] = []
        with httpx.Client(timeout=30.0) as client:
            hdrs = headers_factory() if headers_factory else None
            for _ in range(requests_per_user):
                kwargs = {"headers": hdrs} if hdrs else {}
                out.append(timed_request(client, "GET", f"{api}{path}", **kwargs))
        return out

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=users) as pool:
        futs = [pool.submit(worker, i) for i in range(users)]
        for fut in as_completed(futs):
            samples.extend(fut.result())
    wall = time.perf_counter() - t0
    summary = summarize(samples)
    ok = summary["ok"] or 0
    return {
        "users": users,
        "requests_per_user": requests_per_user,
        "total_requests": len(samples),
        "wall_seconds": wall,
        "throughput_rps": (ok / wall) if wall > 0 else None,
        "summary": summary,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--api", default=os.environ.get("API_BASE_URL", "http://127.0.0.1:18000"))
    p.add_argument("--ui", default=os.environ.get("UI_BASE_URL", "http://127.0.0.1:13000"))
    p.add_argument("--nginx", default=os.environ.get("NGINX_BASE_URL", "http://127.0.0.1:18080"))
    p.add_argument("--reproduce-runs", type=int, default=5)
    p.add_argument("--reproduce-attempts", type=int, default=10)
    p.add_argument("--samples", type=int, default=40)
    p.add_argument("--out", default="loadtests/artifacts/bench_verify.json")
    p.add_argument("--skip-load", action="store_true")
    args = p.parse_args()

    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "api": args.api,
        "ui": args.ui,
        "nginx": args.nginx,
        "methodology": {
            "client": "httpx",
            "timeout_s": 30,
            "percentiles": "nearest-rank linear interpolation",
            "auth": "POST /api/v1/auth/login JSON email/password → Bearer access_token",
        },
    }

    print("=== PHASE 1 reproduce login (host->API) ===", flush=True)
    report["reproduce_login"] = reproduce_login_failures(
        args.api, args.reproduce_runs, args.reproduce_attempts
    )

    print("=== warm / unauthenticated benches ===", flush=True)
    with httpx.Client(timeout=30.0) as client:
        report["unauthenticated"] = [
            bench_endpoint(client, "api_live", "GET", f"{args.api}/live", args.samples),
            bench_endpoint(client, "api_ready", "GET", f"{args.api}/api/v1/ops/ready", args.samples),
            bench_endpoint(client, "nginx_live", "GET", f"{args.nginx}/live", args.samples),
            bench_endpoint(client, "nginx_health", "GET", f"{args.nginx}/health", args.samples),
            bench_endpoint(client, "ui_login_page", "GET", f"{args.ui}/auth/login", min(20, args.samples)),
        ]

    print("=== authentication benches ===", flush=True)
    login_samples: list[Sample] = []
    token: Optional[str] = None
    with httpx.Client(timeout=30.0) as client:
        for _ in range(args.samples):
            tok, s = login(client, args.api)
            login_samples.append(s)
            if tok:
                token = tok
        report["login"] = summarize(login_samples)
        report["login_token_obtained"] = bool(token)

        if token:
            headers = {"Authorization": f"Bearer {token}"}
            # invalid / expired style checks (functional, not latency-primary)
            bad = timed_request(
                client, "GET", f"{args.api}/api/v1/metrics/dashboard", headers={"Authorization": "Bearer not-a-jwt"}
            )
            report["auth_invalid_token"] = asdict(bad)
            report["authenticated"] = [
                bench_endpoint(
                    client, "metrics_dashboard", "GET", f"{args.api}/api/v1/metrics/dashboard", args.samples, headers
                ),
                bench_endpoint(
                    client, "queries_list", "GET", f"{args.api}/api/v1/queries?limit=20", args.samples, headers
                ),
                bench_endpoint(
                    client, "pipelines_list", "GET", f"{args.api}/api/v1/pipelines", args.samples, headers
                ),
            ]
            # one query detail if available
            try:
                qr = client.get(f"{args.api}/api/v1/queries?limit=1", headers=headers, timeout=30.0)
                items = qr.json().get("items") or qr.json() if qr.status_code == 200 else []
                if isinstance(items, dict):
                    items = items.get("items") or []
                if items:
                    qid = items[0]["id"]
                    report["authenticated"].append(
                        bench_endpoint(
                            client,
                            "query_detail",
                            "GET",
                            f"{args.api}/api/v1/queries/{qid}",
                            min(20, args.samples),
                            headers,
                        )
                    )
            except Exception as exc:  # noqa: BLE001
                report["query_detail_error"] = str(exc)[:300]
        else:
            report["authenticated"] = "NOT_VERIFIED"
            report["authenticated_reason"] = "Could not obtain access_token after login samples"

    if not args.skip_load and token:
        print("=== load levels (authenticated metrics) ===", flush=True)
        headers_factory = lambda: {"Authorization": f"Bearer {token}"}  # noqa: E731
        report["load"] = {}
        for users in (10, 25, 50, 100):
            # keep total work bounded
            rpu = max(2, 100 // users)
            print(f"[load] users={users} rpu={rpu}", flush=True)
            report["load"][str(users)] = concurrent_load(
                args.api, "/api/v1/metrics/dashboard", users, rpu, headers_factory
            )
            time.sleep(1)
        report["load_live"] = {}
        for users in (10, 25, 50, 100):
            rpu = max(2, 100 // users)
            report["load_live"][str(users)] = concurrent_load(args.api, "/live", users, rpu, None)
            time.sleep(0.5)
    elif not token:
        report["load"] = "NOT_VERIFIED"
        report["load_reason"] = "No token"

    os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"Wrote {args.out}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
