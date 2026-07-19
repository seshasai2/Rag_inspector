#!/usr/bin/env python3
"""Authenticated latency + load after respecting login rate limits."""
from __future__ import annotations

import concurrent.futures
import json
import math
import statistics
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

API = "http://127.0.0.1:18000"
EMAIL = "demo@example.com"
PASSWORD = "DemoPass123!"


def pct(xs: list[float], q: float) -> Optional[float]:
    if not xs:
        return None
    xs = sorted(xs)
    k = (len(xs) - 1) * q
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return xs[int(k)]
    return xs[f] * (c - k) + xs[c] * (k - f)


def summarize(xs: list[float], fails: int, n: int) -> dict[str, Any]:
    return {
        "n": n,
        "ok": len(xs),
        "fail": fails,
        "error_rate": fails / n if n else None,
        "min_ms": min(xs) if xs else None,
        "max_ms": max(xs) if xs else None,
        "avg_ms": statistics.fmean(xs) if xs else None,
        "stdev_ms": statistics.pstdev(xs) if len(xs) > 1 else (0.0 if xs else None),
        "p50_ms": pct(xs, 0.50),
        "p75_ms": pct(xs, 0.75),
        "p90_ms": pct(xs, 0.90),
        "p95_ms": pct(xs, 0.95),
        "p99_ms": pct(xs, 0.99),
    }


def obtain_token(max_attempts: int = 8) -> tuple[Optional[str], list[dict[str, Any]]]:
    attempts = []
    token = None
    with httpx.Client(timeout=30.0) as c:
        for i in range(max_attempts):
            t0 = time.perf_counter()
            try:
                r = c.post(
                    f"{API}/api/v1/auth/login",
                    json={"email": EMAIL, "password": PASSWORD},
                )
                ms = (time.perf_counter() - t0) * 1000
                attempts.append({"i": i + 1, "status": r.status_code, "ms": ms})
                print(f"login attempt {i+1}: {r.status_code} {ms:.1f}ms", flush=True)
                if r.status_code == 200:
                    token = r.json().get("access_token")
                    break
                if r.status_code == 429:
                    time.sleep(15)
                else:
                    time.sleep(2)
            except Exception as exc:  # noqa: BLE001
                ms = (time.perf_counter() - t0) * 1000
                attempts.append({"i": i + 1, "status": None, "ms": ms, "error": type(exc).__name__})
                print(f"login attempt {i+1}: EXC {type(exc).__name__}", flush=True)
                time.sleep(2)
    return token, attempts


def bench_get(path: str, headers: dict[str, str], n: int) -> dict[str, Any]:
    xs: list[float] = []
    fails = 0
    err: dict[str, int] = {}
    with httpx.Client(timeout=30.0) as c:
        for _ in range(n):
            t0 = time.perf_counter()
            try:
                r = c.get(API + path, headers=headers)
                ms = (time.perf_counter() - t0) * 1000
                if 200 <= r.status_code < 400:
                    xs.append(ms)
                else:
                    fails += 1
                    err[f"http_{r.status_code}"] = err.get(f"http_{r.status_code}", 0) + 1
            except Exception as exc:  # noqa: BLE001
                fails += 1
                key = type(exc).__name__
                err[key] = err.get(key, 0) + 1
    out = summarize(xs, fails, n)
    out["fail_errors"] = err
    out["path"] = path
    return out


def load(path: str, users: int, rpu: int, headers: Optional[dict[str, str]]) -> dict[str, Any]:
    def worker(_: int) -> list[tuple[bool, float, str]]:
        rows: list[tuple[bool, float, str]] = []
        with httpx.Client(timeout=30.0) as c:
            for _ in range(rpu):
                t0 = time.perf_counter()
                try:
                    kwargs = {"headers": headers} if headers else {}
                    r = c.get(API + path, **kwargs)
                    ms = (time.perf_counter() - t0) * 1000
                    rows.append((200 <= r.status_code < 400, ms, f"http_{r.status_code}"))
                except Exception as exc:  # noqa: BLE001
                    ms = (time.perf_counter() - t0) * 1000
                    rows.append((False, ms, type(exc).__name__))
        return rows

    t0 = time.perf_counter()
    all_rows: list[tuple[bool, float, str]] = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=users) as ex:
        futs = [ex.submit(worker, i) for i in range(users)]
        for fut in concurrent.futures.as_completed(futs):
            all_rows.extend(fut.result())
    wall = time.perf_counter() - t0
    oks = [m for ok, m, _ in all_rows if ok]
    fails = len(all_rows) - len(oks)
    err: dict[str, int] = {}
    for ok, _, e in all_rows:
        if not ok:
            err[e] = err.get(e, 0) + 1
    return {
        "users": users,
        "rpu": rpu,
        "wall_s": wall,
        "throughput_rps": (len(oks) / wall) if wall else None,
        "summary": summarize(oks, fails, len(all_rows)),
        "fail_errors": err,
        "path": path,
    }


def main() -> None:
    print("Waiting 70s for AUTH_LOGIN_LIMIT window...", flush=True)
    time.sleep(70)
    token, attempts = obtain_token()
    report: dict[str, Any] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "login_attempts": attempts,
        "token_ok": bool(token),
    }
    if not token:
        report["authenticated"] = "NOT_VERIFIED"
        open("loadtests/artifacts/bench_auth_load.json", "w", encoding="utf-8").write(
            json.dumps(report, indent=2)
        )
        print("NO TOKEN", flush=True)
        return

    h = {"Authorization": f"Bearer {token}"}
    report["invalid_token_status"] = httpx.get(
        f"{API}/api/v1/metrics/dashboard",
        headers={"Authorization": "Bearer not-a-jwt"},
        timeout=30,
    ).status_code
    report["missing_auth_status"] = httpx.get(
        f"{API}/api/v1/metrics/dashboard", timeout=30
    ).status_code

    # login latency sample with spacing to avoid 429 (1 every 4s ≈ 15/min safe under 20/min if that's the limit)
    login_xs: list[float] = []
    login_fail = 0
    with httpx.Client(timeout=30.0) as c:
        for i in range(15):
            t0 = time.perf_counter()
            r = c.post(f"{API}/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
            ms = (time.perf_counter() - t0) * 1000
            if r.status_code == 200:
                login_xs.append(ms)
                token = r.json().get("access_token") or token
            else:
                login_fail += 1
            time.sleep(4)
    h = {"Authorization": f"Bearer {token}"}
    report["login_spaced"] = summarize(login_xs, login_fail, 15)

    report["authenticated"] = {
        "metrics_dashboard": bench_get("/api/v1/metrics/dashboard", h, 40),
        "queries_list": bench_get("/api/v1/queries?limit=20", h, 40),
        "pipelines_list": bench_get("/api/v1/pipelines", h, 30),
    }
    r = httpx.get(f"{API}/api/v1/queries?limit=1", headers=h, timeout=30)
    items = r.json().get("items") or []
    if items:
        report["authenticated"]["query_detail"] = bench_get(
            f"/api/v1/queries/{items[0]['id']}", h, 20
        )

    report["load_metrics"] = {
        str(u): load("/api/v1/metrics/dashboard", u, max(2, 80 // u), h)
        for u in (10, 25, 50, 100)
    }
    report["load_live"] = {
        str(u): load("/live", u, max(2, 80 // u), None) for u in (10, 25, 50, 100)
    }

    # refresh token path if available from last login body — skip if unknown
    report["refresh"] = "NOT_VERIFIED"
    report["refresh_reason"] = "Harness uses access_token only; refresh cookie/body not captured this run"

    path = "loadtests/artifacts/bench_auth_load.json"
    open(path, "w", encoding="utf-8").write(json.dumps(report, indent=2))
    print(json.dumps({k: report[k] for k in report if k != "login_attempts"}, indent=2)[:5000])
    print(f"Wrote {path}", flush=True)


if __name__ == "__main__":
    main()
