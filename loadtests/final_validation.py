#!/usr/bin/env python3
"""Final independent performance validation harness.

Produces loadtests/artifacts/final_validation.json (+ simple SVG charts).
Does not change application rate limits.
"""
from __future__ import annotations

import json
import math
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import httpx

API = "http://127.0.0.1:18000"
UI = "http://127.0.0.1:13000"
EMAIL = "demo@example.com"
PASSWORD = "DemoPass123!"
OUT = Path("loadtests/artifacts")
OUT.mkdir(parents=True, exist_ok=True)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


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


def summary(xs: list[float], fails: int = 0, n: Optional[int] = None) -> dict[str, Any]:
    n = n if n is not None else len(xs) + fails
    return {
        "n": n,
        "ok": len(xs),
        "fail": fails,
        "error_rate": (fails / n) if n else None,
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


def write_svg_line(path: Path, title: str, series: list[tuple[float, float]], ylabel: str) -> None:
    """Minimal SVG line chart (x,y samples). No matplotlib required."""
    if len(series) < 2:
        path.write_text(f"<svg xmlns='http://www.w3.org/2000/svg'><text x='10' y='20'>{title}: insufficient points</text></svg>")
        return
    w, h, pad = 720, 280, 40
    xs = [p[0] for p in series]
    ys = [p[1] for p in series]
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if ymax <= ymin:
        ymax = ymin + 1
    if xmax <= xmin:
        xmax = xmin + 1

    def sx(x: float) -> float:
        return pad + (x - xmin) / (xmax - xmin) * (w - 2 * pad)

    def sy(y: float) -> float:
        return h - pad - (y - ymin) / (ymax - ymin) * (h - 2 * pad)

    pts = " ".join(f"{sx(x):.1f},{sy(y):.1f}" for x, y in series)
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}">
  <rect width="100%" height="100%" fill="#0f172a"/>
  <text x="{pad}" y="24" fill="#e2e8f0" font-family="Segoe UI,sans-serif" font-size="14">{title}</text>
  <text x="{pad}" y="{h-8}" fill="#94a3b8" font-family="Segoe UI,sans-serif" font-size="11">{ylabel} (min={ymin:.1f} max={ymax:.1f})</text>
  <polyline fill="none" stroke="#38bdf8" stroke-width="2" points="{pts}"/>
</svg>"""
    path.write_text(svg, encoding="utf-8")


def wait_for_login_budget(c: httpx.Client, max_wait_s: int = 90) -> dict[str, Any]:
    t0 = time.time()
    attempts = []
    while time.time() - t0 < max_wait_s:
        r = c.post(f"{API}/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
        attempts.append({"status": r.status_code, "ts": now()})
        if r.status_code == 200:
            return {"ok": True, "attempts": attempts, "body": r.json()}
        if r.status_code == 429:
            time.sleep(10)
        else:
            time.sleep(2)
    return {"ok": False, "attempts": attempts}


def prove_rate_limit(c: httpx.Client) -> dict[str, Any]:
    """Burn budget until 429; capture status/body/headers. Then one spaced success after wait."""
    results = []
    for i in range(25):
        t0 = time.perf_counter()
        r = c.post(f"{API}/api/v1/auth/login", json={"email": EMAIL, "password": PASSWORD})
        ms = (time.perf_counter() - t0) * 1000
        results.append(
            {
                "i": i + 1,
                "status": r.status_code,
                "ms": ms,
                "retry_after": r.headers.get("Retry-After") or r.headers.get("retry-after"),
                "body_preview": (r.text or "")[:240],
            }
        )
        if r.status_code == 429 and i >= 19:
            break
        time.sleep(0.05)
    statuses = [x["status"] for x in results]
    first_429 = next((i for i, s in enumerate(statuses) if s == 429), None)
    return {
        "attempts": results,
        "first_429_index_1based": None if first_429 is None else first_429 + 1,
        "success_before_429": sum(1 for s in statuses if s == 200),
        "matches_20_per_minute_budget": (first_429 == 20) or (sum(1 for s in statuses if s == 200) == 20),
        "transport_errors": 0,
        "conclusion": "HTTP_429_AFTER_BUDGET" if 429 in statuses else "NO_429_UNEXPECTED",
    }


def measure_auth_paths(c: httpx.Client, login_body: dict[str, Any]) -> dict[str, Any]:
    access = login_body["access_token"]
    refresh = login_body["refresh_token"]
    out: dict[str, Any] = {}

    # protected
    xs = []
    fails = 0
    for _ in range(25):
        t0 = time.perf_counter()
        r = c.get(f"{API}/api/v1/metrics/dashboard", headers={"Authorization": f"Bearer {access}"})
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code == 200:
            xs.append(ms)
        else:
            fails += 1
    out["protected_dashboard"] = summary(xs, fails)

    # invalid / missing
    r_bad = c.get(f"{API}/api/v1/metrics/dashboard", headers={"Authorization": "Bearer not-a-jwt"})
    r_miss = c.get(f"{API}/api/v1/metrics/dashboard")
    out["invalid_token_status"] = r_bad.status_code
    out["missing_auth_status"] = r_miss.status_code

    # refresh latency (n=8) — each refresh rotates token
    refresh_xs = []
    refresh_fail = 0
    cur_refresh = refresh
    cur_access = access
    for _ in range(8):
        t0 = time.perf_counter()
        r = c.post(f"{API}/api/v1/auth/refresh", json={"refresh_token": cur_refresh})
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code == 200:
            refresh_xs.append(ms)
            data = r.json()
            cur_refresh = data["refresh_token"]
            cur_access = data["access_token"]
        else:
            refresh_fail += 1
            break
        time.sleep(0.2)
    out["refresh"] = summary(refresh_xs, refresh_fail, 8)
    out["refresh_still_works_status"] = c.get(
        f"{API}/api/v1/pipelines", headers={"Authorization": f"Bearer {cur_access}"}
    ).status_code

    # logout
    t0 = time.perf_counter()
    r_out = c.post(f"{API}/api/v1/auth/logout", json={"refresh_token": cur_refresh})
    out["logout"] = {
        "status": r_out.status_code,
        "ms": (time.perf_counter() - t0) * 1000,
        "body_preview": (r_out.text or "")[:200],
    }
    # refresh after logout should fail
    r_after = c.post(f"{API}/api/v1/auth/refresh", json={"refresh_token": cur_refresh})
    out["refresh_after_logout_status"] = r_after.status_code
    return out


def measure_cache(c: httpx.Client, access: str) -> dict[str, Any]:
    h = {"Authorization": f"Bearer {access}"}
    # force miss by unique pipeline filter none + wait TTL unlikely; first call miss, second hit within TTL
    samples = []
    for i in range(12):
        t0 = time.perf_counter()
        r = c.get(f"{API}/api/v1/metrics/dashboard", headers=h)
        ms = (time.perf_counter() - t0) * 1000
        samples.append({"i": i + 1, "ms": ms, "status": r.status_code, "x_cache": r.headers.get("X-Cache")})
        time.sleep(0.05)
    hits = [s for s in samples if (s["x_cache"] or "").lower() == "hit"]
    misses = [s for s in samples if (s["x_cache"] or "").lower() == "miss"]
    return {
        "samples": samples,
        "hit_count": len(hits),
        "miss_count": len(misses),
        "hit_latency": summary([s["ms"] for s in hits]) if hits else "NOT_VERIFIED",
        "miss_latency": summary([s["ms"] for s in misses]) if misses else "NOT_VERIFIED",
    }


def measure_eval_pipeline(c: httpx.Client, access: str) -> dict[str, Any]:
    """Create API key, ingest one trace, poll until analysis completes or timeout."""
    h = {"Authorization": f"Bearer {access}"}
    # pipelines
    pipes = c.get(f"{API}/api/v1/pipelines", headers=h)
    if pipes.status_code != 200:
        return {"status": "NOT_VERIFIED", "reason": f"pipelines {pipes.status_code}"}
    items = pipes.json()
    if isinstance(items, dict):
        items = items.get("items") or items.get("pipelines") or []
    if not items:
        return {"status": "NOT_VERIFIED", "reason": "no pipelines"}
    pipeline_id = items[0]["id"] if isinstance(items[0], dict) else items[0]

    kr = c.post(f"{API}/api/v1/keys", headers=h, json={"name": f"bench-{int(time.time())}", "scopes": ["ingest:write"]})
    if kr.status_code not in (200, 201):
        return {"status": "NOT_VERIFIED", "reason": f"create key {kr.status_code} {kr.text[:200]}"}
    key_body = kr.json()
    api_key = key_body.get("raw_key") or key_body.get("key") or key_body.get("api_key")
    if not api_key:
        return {"status": "NOT_VERIFIED", "reason": f"no raw key in {list(key_body.keys())}"}

    payload = {
        "pipeline_id": str(pipeline_id),
        "query": "What is the refund policy for delayed shipments?",
        "answer": "Refunds are available within 30 days if the shipment is delayed beyond the SLA.",
        "retrieved_chunks": [
            {
                "chunk_id": "c1",
                "text": "Customers may request a refund within 30 days when delivery exceeds the published SLA.",
                "score": 0.91,
                "rank": 1,
            },
            {
                "chunk_id": "c2",
                "text": "Store credit may be offered as an alternative to cash refunds.",
                "score": 0.55,
                "rank": 2,
            },
        ],
    }
    t_ingest0 = time.perf_counter()
    ir = c.post(
        f"{API}/api/v1/ingest/trace",
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        json=payload,
    )
    ingest_ms = (time.perf_counter() - t_ingest0) * 1000
    if ir.status_code not in (200, 201, 202):
        return {
            "status": "NOT_VERIFIED",
            "reason": f"ingest {ir.status_code}",
            "body": ir.text[:300],
            "ingest_ms": ingest_ms,
        }
    body = ir.json()
    trace_id = body.get("id") or body.get("trace_id") or body.get("query_id")
    if not trace_id:
        return {"status": "NOT_VERIFIED", "reason": f"no trace id keys={list(body.keys())}", "ingest_ms": ingest_ms}

    # poll query detail / list for analysis_status
    t_wait0 = time.perf_counter()
    final = None
    polls = []
    deadline = time.time() + 180
    while time.time() < deadline:
        t0 = time.perf_counter()
        dr = c.get(f"{API}/api/v1/queries/{trace_id}", headers=h)
        poll_ms = (time.perf_counter() - t0) * 1000
        st = None
        if dr.status_code == 200:
            final = dr.json()
            st = final.get("analysis_status")
        polls.append({"ts": now(), "status_code": dr.status_code, "analysis_status": st, "poll_ms": poll_ms})
        if st in ("completed", "failed"):
            break
        time.sleep(1.0)
    queue_wait_ms = (time.perf_counter() - t_wait0) * 1000
    if not final:
        return {
            "status": "NOT_VERIFIED",
            "reason": "timeout waiting for analysis",
            "ingest_ms": ingest_ms,
            "queue_wait_ms": queue_wait_ms,
            "polls": polls[-5:],
        }

    # component latencies if present on trace (from SDK fields) + trust score presence
    return {
        "status": "VERIFIED" if final.get("analysis_status") == "completed" else final.get("analysis_status"),
        "ingest_ms": ingest_ms,
        "queue_plus_worker_wait_ms": queue_wait_ms,
        "analysis_status": final.get("analysis_status"),
        "trustworthiness_score": final.get("trustworthiness_score"),
        "grounded_fraction": final.get("grounded_fraction"),
        "embed_latency_ms_field": final.get("embed_latency_ms"),
        "retrieve_latency_ms_field": final.get("retrieve_latency_ms"),
        "generate_latency_ms_field": final.get("generate_latency_ms"),
        "rank_latency_ms_field": final.get("rank_latency_ms"),
        "note": "embed/retrieve/generate/rank fields are client-reported SDK timings if present; worker NLI/Trust timing is included in queue_plus_worker_wait_ms end-to-end",
        "polls": len(polls),
    }


def measure_ui(c: httpx.Client) -> dict[str, Any]:
    xs = []
    fails = 0
    for _ in range(15):
        t0 = time.perf_counter()
        r = c.get(f"{UI}/auth/login")
        ms = (time.perf_counter() - t0) * 1000
        if r.status_code == 200:
            xs.append(ms)
        else:
            fails += 1
    # dashboard HTML requires auth cookies — measure redirect/login only; mark dashboard render NOT_VERIFIED without browser
    return {
        "login_page_ttfb_proxy": summary(xs, fails),
        "dashboard_rendering": "NOT_VERIFIED",
        "dashboard_rendering_reason": "Requires browser session cookies; httpx only measured login document TTFB",
        "browser": "NOT_USED",
    }


def main() -> None:
    report: dict[str, Any] = {
        "generated_at": now(),
        "api": API,
        "methodology": "independent final_validation.py / httpx",
    }
    transport_errors = 0
    with httpx.Client(timeout=60.0) as c:
        print("Waiting for login budget...", flush=True)
        boot = wait_for_login_budget(c)
        report["budget_wait"] = {"ok": boot.get("ok"), "attempts": len(boot.get("attempts") or [])}
        if not boot.get("ok"):
            report["fatal"] = "Could not login within wait window"
            (OUT / "final_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
            return

        print("Proving rate limit...", flush=True)
        # use a fresh client identity is same IP — prove 429
        report["rate_limit_proof"] = prove_rate_limit(c)

        print("Waiting 65s for budget reset after proof...", flush=True)
        time.sleep(65)
        boot2 = wait_for_login_budget(c, max_wait_s=90)
        if not boot2.get("ok"):
            report["auth_paths"] = "NOT_VERIFIED"
            report["auth_paths_reason"] = "login failed after rate-limit proof wait"
        else:
            login_body = boot2["body"]
            print("Auth paths...", flush=True)
            report["auth_paths"] = measure_auth_paths(c, login_body)
            # new login for remaining tests (logout consumed refresh)
            time.sleep(4)
            boot3 = wait_for_login_budget(c, max_wait_s=90)
            if boot3.get("ok"):
                access = boot3["body"]["access_token"]
                print("Cache...", flush=True)
                report["redis_dashboard_cache"] = measure_cache(c, access)
                print("Eval pipeline...", flush=True)
                report["eval_pipeline"] = measure_eval_pipeline(c, access)
                # unauth health
                live_xs = []
                for _ in range(30):
                    t0 = time.perf_counter()
                    try:
                        r = c.get(f"{API}/live")
                        if r.status_code == 200:
                            live_xs.append((time.perf_counter() - t0) * 1000)
                        else:
                            transport_errors += 1
                    except Exception:
                        transport_errors += 1
                report["live"] = summary(live_xs)
                report["ui"] = measure_ui(c)
            else:
                report["post_logout_login"] = "NOT_VERIFIED"

    report["hidden_transport_failures_in_this_script"] = transport_errors
    report["component_latency_notes"] = {
        "embedding_latency": "NOT_VERIFIED as isolated worker stage — only SDK field embed_latency_ms if client sent it",
        "retrieval_latency": "NOT_VERIFIED as isolated worker stage — retrieve_latency_ms field if present",
        "reranking_latency": "NOT_VERIFIED — no dedicated rerank timer endpoint",
        "trust_score_calculation_latency": "NOT_VERIFIED in isolation — included in analysis e2e wait",
        "database_query_latency": "NOT_VERIFIED — no pg_stat_statements export this pass",
        "worker_stage_breakdown": "NOT_VERIFIED — end-to-end analysis wait only",
    }

    (OUT / "final_validation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    # charts from rate limit statuses and live latencies
    if isinstance(report.get("live"), dict) and report["live"].get("ok"):
        # synthetic chart from live summary only — detailed series in soak
        pass
    rl = report.get("rate_limit_proof") or {}
    if rl.get("attempts"):
        series = [(float(a["i"]), 1.0 if a["status"] == 200 else 0.0) for a in rl["attempts"]]
        write_svg_line(OUT / "chart_login_success_vs_attempt.svg", "Login success (1) vs fail (0) by attempt", series, "success")
        series2 = [(float(a["i"]), float(a["ms"])) for a in rl["attempts"] if a["status"] == 200]
        if series2:
            write_svg_line(OUT / "chart_login_latency.svg", "Login latency (successful only)", series2, "ms")
    print("Wrote", OUT / "final_validation.json", flush=True)


if __name__ == "__main__":
    main()
