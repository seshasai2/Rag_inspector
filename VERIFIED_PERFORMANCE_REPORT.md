# RAGInspector — Verified Performance Report

**Date:** 2026-07-19  
**Role:** Independent Performance Verification Engineer  
**Prior report under review:** [PERFORMANCE_BENCHMARK_REPORT.md](PERFORMANCE_BENCHMARK_REPORT.md)  
**Rule:** No fabricated success. Unverified items marked **NOT VERIFIED**.

---

## 1. Verdict on prior benchmark report

| Claim from prior report | Independent re-check | Trust |
|-------------------------|----------------------|-------|
| HTTP 429 after ~20 logins/min is intentional SlowAPI limit | **CONFIRMED** — body `{"error":"Rate limit exceeded: 20 per 1 minute"}` at attempt 20 (1 login used in budget wait + 19 in proof loop) | **High** |
| No auth bugs for login/refresh/logout/protected routes | **CONFIRMED** — invalid/missing → 401; refresh n=8 OK; logout 200; refresh-after-logout 401 | **High** |
| Hidden transport failures dominant | **PARTIALLY** — 0 in validation script; soak saw **3** timeouts/protocol errors in 30 min (~0.1%) | **Medium** |
| Unauth /live ~p50 6–7 ms | **CONFIRMED** (re-run n=30 p50 6.0 ms) | **High** |
| Auth dashboard single-thread ~p50 10–16 ms | **CONFIRMED** (n=25 p50 16.7 ms) | **High** |
| Concurrent dashboard multi-second p95 on this laptop | Accepted as **hardware/contention** (not re-run at 100 VU this pass; prior artifact retained) | **Medium** |
| Evaluation pipeline latency | Was NOT VERIFIED → **now VERIFIED** (see §6) | **High** (single sample) |
| Prometheus useful for this stack | Was NOT VERIFIED → scrape was **broken** → **fixed** → `up=1` | **High** |

**Overall trust in prior report’s core RCA (429):** High.  
**Overall trust in prior report as complete production evidence:** Medium — gaps remain (cold start, isolated stage timers, Grafana PNG, exporter targets).

---

## 2. Environment (production context)

| Item | Value | Class |
|------|-------|-------|
| OS | Windows 11 Home 10.0.26200 | Dev machine |
| Host | HP Victus 16-e0xxx | Dev machine |
| CPU | 12 logical processors | Dev machine |
| RAM | ~7.3 GiB | Dev machine (**limitation**) |
| Docker | 29.3.1 Desktop | Dev machine |
| Compose | verify-ports + observability (prometheus/grafana) | App |
| API/UI/Nginx | `:18000` / `:13000` / `:18080` | App |
| Competing containers | Many `ifg-*` + raginspector_* | Dev machine (**limitation**) |
| Browser for UI dashboards | **NOT USED** (httpx / Locust / k6 only) | — |
| Docker resource limits | Compose defaults; worker ~870 MiB RSS observed | Mixed |

**Do not attribute** multi-second concurrent p95 or host `ReadTimeout` solely to application logic without a quiet dedicated host.

---

## 3. Methodology & artifacts

| Artifact | Purpose |
|----------|---------|
| `loadtests/artifacts/final_validation.json` | Rate-limit proof, auth, cache, live, UI TTFB |
| `loadtests/artifacts/eval_pipeline.json` | Ingest → analysis complete |
| `loadtests/artifacts/soak_30m.json` | 30 min soak + docker stats |
| `loadtests/artifacts/k6_smoke.txt` | k6 10 VU / 1 m via Docker image |
| `loadtests/artifacts/locust_10vu.txt` | Locust 10 users / 60 s |
| `loadtests/artifacts/prometheus_*.json` | Prometheus `up` queries |
| `loadtests/artifacts/chart_*.svg` | Charts |
| `loadtests/artifacts/grafana_login.html` | Grafana login HTML (host PNG **failed**) |
| `backend/app/api/v1/endpoints/ops.py` | Metrics PlainTextResponse fix |

Client tools: httpx, Grafana k6 Docker `grafana/k6:0.54.0`, Locust 2.45.0.

---

## 4. Rate limit = intentional (only cause of systematic login failure)

Evidence (`final_validation.json` → `rate_limit_proof`):

- Attempts 1–19 in proof loop: **HTTP 200**
- Attempt 20: **HTTP 429**, body: `Rate limit exceeded: 20 per 1 minute`
- `Retry-After` header: absent (SlowAPI default)
- Transport errors during proof: **0**
- Code: `AUTH_LOGIN_LIMIT = "20/minute"` in `backend/app/core/rate_limit.py`

**Confidence: High** — not an auth bug.

---

## 5. Authentication verification

| Test | Result | Confidence |
|------|--------|------------|
| Login | 200 + tokens | High |
| Protected dashboard | n=25, 0% err, p50 16.7 ms, p95 58.5 ms | High |
| Invalid Bearer | 401 | High |
| Missing auth | 401 | High |
| JWT refresh | n=8, 0% err, p50 35 ms, p95 194 ms | High |
| After refresh, pipelines | 200 | High |
| Logout | 200, 64 ms, `Logged out` | High |
| Refresh after logout | 401 | High |
| Concurrent sessions / CSRF / cookies | **NOT VERIFIED** | — |

---

## 6. Missing evidence — collected vs still open

| Metric | Status | Result / why |
|--------|--------|--------------|
| k6 load | **Verified (smoke)** | 10 VU × 1 m; http_req_duration p95 ~64–75 ms; live p95 ~41 ms; ready p95 ~102–134 ms |
| Locust | **Verified (10 VU / 60s)** | 50 req aggregated, **0% fails**; login avg ~621–972 ms |
| Cold vs warm startup | **NOT VERIFIED** | Would require controlled stop/start of ML worker; not done during soak |
| JWT refresh latency | **Verified** | See §5 |
| Logout latency | **Verified** | 64 ms (n=1) — confidence Medium (single sample) |
| Protected endpoint latency | **Verified** | Dashboard §5 |
| RAG evaluation e2e | **Verified** | ingest 2221 ms → wait 7743 ms → `completed`; Trust 90.9; grounded 1.0; BM25 present |
| Retrieval / embedding / rank fields | **Partial** | Client-reported fields echoed (embed 12.5, retrieve 45, generate 220); rank null; **not** worker-stage timers |
| Reranking latency | **NOT VERIFIED** | No isolated timer |
| Trust Score calc alone | **NOT VERIFIED** | Included in e2e wait only |
| Dashboard rendering (browser) | **NOT VERIFIED** | No browser session |
| DB query latency | **NOT VERIFIED** | No pg_stat_statements |
| Redis hit latency | **Verified** | X-Cache=hit ×12, p50 ~14.1 ms |
| Redis miss latency | **NOT VERIFIED** | All samples were hits (warm cache) |
| Worker / queue latency | **Partial** | e2e analysis wait 7.7 s (includes queue + NLI etc.) |
| Background throughput | **NOT VERIFIED** | Single ingest only |

---

## 7. Infrastructure metrics

### Docker health during soak (30 min)

| Check | Result |
|-------|--------|
| Duration | 1801 s |
| live OK / fail | 1568 / **1** (ReadTimeout) |
| dashboard OK / fail | 1567 / **2** (ReadTimeout + RemoteProtocolError) |
| Error rate | ~0.1% |
| Container restarts | **0** (backend/worker/db/redis/frontend) |
| Backend mem (docker stats) | ~239 → ~504 MiB across samples (chart: `chart_soak_backend_mem.svg`) |
| Memory leak? | **Inconclusive** — growth observed; may be caches/pools; no OOM; **not** proven leak |

### Prometheus / Grafana

| Item | Result |
|------|--------|
| Prometheus ready | Yes (in-container) |
| Backend `up` **before** fix | **0** — metrics JSON-encoded |
| Backend `up` **after** PlainTextResponse fix | **1** |
| Exporters (postgres/redis/cadvisor/node) | `up=0` — containers not started (only prometheus+grafana brought up) |
| Grafana | Container up; login HTML captured via `docker exec`; **host PNG screenshot NOT VERIFIED** (connection reset to `:13001`) |
| Host→`:19090` | Intermittent connection reset (Docker Desktop) — use in-network queries for evidence |

### Proven fix applied

`GET /api/v1/ops/metrics` now returns `PlainTextResponse` (`text/plain; version=0.0.4`).  
Unit test: `backend/tests/unit/test_ops_metrics_plaintext.py`.

---

## 8. Soak test summary

| Metric | Value | Confidence |
|--------|------:|------------|
| Sustained RPS (approx) | ~1.7 req/s combined live+dash | Medium |
| Error rate | ~0.1% | High |
| Restarts | 0 | High |
| Throughput stability | Stable OK counts linearly with time | High |
| Resource leak | **NOT VERIFIED** (growth without leak proof) | Low |

Errors coincided with other heavy activity (k6/validation) around t≈386s — consistent with **host/Docker contention**, not systemic app outage.

---

## 9. Charts & screenshots

| File | Content |
|------|---------|
| `loadtests/artifacts/chart_login_success_vs_attempt.svg` | Login success→429 |
| `loadtests/artifacts/chart_login_latency.svg` | Successful login latency |
| `loadtests/artifacts/chart_soak_backend_mem.svg` | Backend RSS during soak |
| `loadtests/artifacts/grafana_login.html` | Grafana login document |
| Grafana PNG | **NOT VERIFIED** |

---

## 10. k6 / Locust tables

### k6 smoke (10 VU, 1 m) — Docker → host.docker.internal:18000

| Trend | p95 (run A) | p95 (run B) |
|-------|------------:|------------:|
| http_req_duration | 64 ms | 75 ms |
| live | 42 ms | 40 ms |
| health | 25 ms | 36 ms |
| ready | 102 ms | 134 ms |

### Locust (10 users, 60 s, headless)

| Name | #reqs | Fails | Avg | Med |
|------|------:|------:|----:|----:|
| GET /live | 20 | 0% | 83 | 33 |
| GET /health | 13 | 0% | 38 | 9 |
| GET /ready | 10 | 0% | 119 | 42 |
| POST /login | 3 | 0% | 621 | 640 |
| GET /dashboard | 2 | 0% | 69 | 20 |
| **Aggregated** | **50** | **0%** | 146 | 35 |

---

## 11. Evaluation pipeline (single sample)

| Stage | ms | Notes |
|-------|---:|-------|
| Ingest HTTP | 2221 | Includes accept + enqueue |
| Queue + worker to `completed` | 7743 | End-to-end |
| Trust score | 90.9 | Result, not timer |
| Grounded fraction | 1.0 | |
| Grounding results | 1 | |
| BM25 comparison | present | |

**Confidence: Medium** — one trace on warm worker; not a distribution.

---

## 12. Remaining bottlenecks (ranked by expected impact)

| Rank | Item | Type | Expected impact | Action |
|-----:|------|------|-----------------|--------|
| 1 | Prometheus metrics JSON encoding | **App bug (fixed)** | Observability unusable until fix | Shipped PlainTextResponse |
| 2 | Host Docker Desktop publish-port flakes | Dev machine | False “outages” in benches | Prefer WSL2/dedicated host; in-container probes |
| 3 | Login 20/min (and Nginx 5/min) | Intentional | Breaks naive load scripts | Reuse tokens in benches |
| 4 | Concurrent dashboard p95 on 8 GB host | Hardware + contention | Looks like app slowness | Re-bench on quiet host before optimizing SQL |
| 5 | Missing isolated worker stage timers | Instrumentation gap | Can’t tune NLI vs BM25 | Add stage histograms (future) |
| 6 | Cache miss not measured | Test gap | Incomplete Redis story | Force TTL expiry in harness |

**No further app micro-optimizations performed** — only the proven metrics Content-Type bug was fixed.

---

## 13. Final confidence matrix

| Benchmark family | Confidence |
|------------------|------------|
| Rate-limit RCA | **High** |
| Auth correctness | **High** |
| Unauth latency (this host) | **High** |
| Auth protected latency (this host) | **High** |
| Refresh / logout | **High** / **Medium** |
| Redis cache hit | **High** |
| Redis cache miss | **Low** (NOT VERIFIED) |
| k6 smoke | **High** |
| Locust 10 VU | **Medium** (short run) |
| 30 min soak stability | **High** |
| Eval e2e latency | **Medium** (n=1) |
| Cold start | **NOT VERIFIED** |
| Browser dashboard render | **NOT VERIFIED** |
| Production SLO readiness | **Low** |
| Grafana PNG evidence | **NOT VERIFIED** |
| Full exporter stack metrics | **NOT VERIFIED** |

---

## 14. Performance conclusions

1. The previous “authenticated benches failed” finding is **correctly explained by intentional 429 rate limiting**, re-proven with response body evidence.  
2. Authentication flows (login, refresh rotation, logout revoke) behave correctly under test.  
3. Hidden transport failures exist at **very low rate** on this Windows Docker Desktop host; they are **not** the primary login failure mode.  
4. Health and cached dashboard paths are fast on this machine; login is bcrypt-bound (~300–700 ms).  
5. Analysis e2e for one small trace completed in ~**8 s** worker wait after ingest on a warm worker.  
6. Observability had a **real app defect** (metrics as JSON string); after fix, Prometheus `up=1` for the backend job.  
7. Numbers here characterize a **contended 8 GB laptop**, not a production SLA.

**Production readiness (performance evidence): Medium for self-host demo; Low for capacity planning.**
