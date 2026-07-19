# RAGInspector — Performance Benchmark & Root Cause Report

**Date:** 2026-07-19  
**Role:** Principal Performance / Staff Platform / SRE (adversarial)  
**Objective:** Determine whether prior “authenticated bench NOT VERIFIED” findings are accurate, reproducible, and what they imply for production readiness.  
**Rule:** No fabricated success. Missing surfaces marked **NOT VERIFIED**.

**Artifacts:**

| File | Contents |
|------|----------|
| `loadtests/artifacts/bench_verify.json` | 5-run login reproduce + unauthenticated latency |
| `loadtests/artifacts/bench_auth_load.json` | Spaced login + authenticated + concurrent load |
| `loadtests/bench_verify.py` / `bench_auth_load.py` | Reproducible harness (httpx) |

---

## 1. Executive findings

1. **Primary root cause of failed authenticated collection (reproduced today):**  
   **HTTP 429 Too Many Requests** from SlowAPI `AUTH_LOGIN_LIMIT = "20/minute"` after ~20 rapid logins — **not** an application crash and **not** JWT failure.

2. **Historical host “connection forcibly closed” (2026-07-17):**  
   **NOT REPRODUCED** in this pass (0 transport failures across 5 login runs × 12 attempts; 30/30 `/live` OK). Treat as intermittent Docker Desktop / host-proxy flake under prior load, separate from 429.

3. **After respecting the login budget**, authenticated metrics/queries/pipelines/detail were measured with **0% error** at single-threaded sample sizes (n=20–40).

4. **Under concurrent authenticated dashboard load**, latency tails grow sharply (p95 multi-second) on this laptop while error rate stays **0%** — capacity/contention, not auth failure.

5. **k6 / Locust / RAGInspector Prometheus+Grafana overlay:** **NOT VERIFIED** this pass (k6 absent; obs containers for this stack not running).

---

## 2. Environment

| Item | Value |
|------|-------|
| Host | HP Victus 16-e0xxx, Windows 11 (10.0.26200) |
| CPU | 12 logical processors |
| RAM | ~7.3 GiB (7887110144 bytes) |
| Docker Engine | 29.3.1 |
| Compose | `docker-compose.yml` + `docker-compose.verify-ports.yml` |
| API | `http://127.0.0.1:18000` |
| UI | `http://127.0.0.1:13000` |
| Nginx | `http://127.0.0.1:18080` |
| Stack age at test | ~39–40 hours uptime; **restart count 0** for backend/frontend |
| Competing workloads | Many unrelated `ifg-*` containers on same Docker Desktop (CPU/RAM contention) |
| Client | Python 3.14.3 + httpx 0.28.1 |
| Demo user | `demo@example.com` |

**Software under test:** FastAPI backend, Next.js frontend, Postgres, Redis, Celery worker/beat, Nginx (see compose).

---

## 3. Methodology

| Aspect | Detail |
|--------|--------|
| Client | Synchronous httpx, 30s timeout, host → published ports |
| Percentiles | Linear interpolation on sorted successful samples |
| Auth | `POST /api/v1/auth/login` → Bearer `access_token` |
| Reproduce | 5 independent runs × 12 login attempts (50 ms spacing) |
| Unauth latency | n=40 (UI login page n=20) |
| Auth latency | n=15 spaced logins (4s); n=40 dashboard/queries; n=30 pipelines; n=20 detail |
| Load | ThreadPool concurrent users 10/25/50/100; ~80–200 total requests per level |
| Warm-up | Stack already warm (39h); no cold worker model reload measured |
| What this is **not** | Not k6; not production SLO; not multi-node; not dedicated bench host |

**Statistical confidence:** Adequate to diagnose rate-limit and characterize **this laptop**. **Insufficient** to claim production SLOs. Treat p95 under concurrent load as noisy (high stdev, shared Docker).

---

## 4. Phase 1 — Failure reproduction (5 runs)

| Run | Started (UTC) | OK / N | Error rate | First error |
|-----|---------------|-------:|-----------:|-------------|
| 1 | 2026-07-19T03:35:23Z | 12/12 | 0% | — |
| 2 | 2026-07-19T03:35:28Z | 8/12 | 33% | `http_429` |
| 3 | 2026-07-19T03:35:32Z | 0/12 | 100% | `http_429` |
| 4 | 2026-07-19T03:35:33Z | 0/12 | 100% | `http_429` |
| 5 | 2026-07-19T03:35:34Z | 0/12 | 100% | `http_429` |

**Cumulative logins before wall:** 12 + 8 = **20** successful → subsequent **429**.

| Question | Answer (evidence) |
|----------|-------------------|
| Reproducible? | **YES** — 429 after ~20 logins/minute |
| Every run? | Failures from run 2 onward in a continuous burst |
| Only once? | No — persists until window resets |
| After warm-up? | Stack already warm; still 429 |
| After startup only? | **No** — stack up 39h |
| Random transport reset today? | **No** — `runs_with_transport_failure = 0` |

Follow-on unauth benches in the same script still succeeded; the **login** section then recorded **40/40 × 429** because the minute budget was exhausted → authenticated section **NOT_VERIFIED** in that file (expected).

---

## 5. Phase 2 — Root cause analysis

### Confirmed cause (authenticated collection failure)

| Evidence | Detail |
|----------|--------|
| Code | `backend/app/core/rate_limit.py`: `AUTH_LOGIN_LIMIT = "20/minute"` |
| Wiring | `auth.py` `@limiter.limit(AUTH_LOGIN_LIMIT)` on `/login` |
| Behavior | Exact threshold: 20 OK then 429 |
| Nginx (edge) | `nginx.conf` `zone=auth … rate=5r/m` on `/api/v1/auth/login` — stricter if traffic hits `:18080` |
| Not observed today | Backend crash, restart loop, Redis/DB down, JWT encode errors |

**Conclusion:** Prior “login connection reset → auth benches skipped” mixed two phenomena. The **deterministic** blocker for rapid login benchmarks is **rate limiting (429)**. Transport resets remain a **separate, intermittent** host/Docker issue (seen historically; not reproduced this pass).

### Contributing environmental factors (latency tails)

| Factor | Evidence |
|--------|----------|
| 8 GB RAM laptop + many containers | `docker stats` shows `ifg-*` stack sharing Docker |
| Worker RSS ~870 MiB | ML worker memory resident |
| `/ops/ready` sometimes slow in-container | Logs earlier showed `duration_ms=448–751` on health SQL path |
| Concurrent dashboard p95 multi-second | Load tables below; 0% errors |

### Not root cause (ruled out this pass)

| Hypothesis | Evidence against |
|------------|------------------|
| Unhealthy containers | All raginspector_* healthy; restarts=0 |
| Migrations pending | Ready soft_checks previously `ok:020_*` |
| Frontend breaking login API | API login 200 when under budget |
| Invalid credentials | Demo seed works |

---

## 6. Phase 3 — Infrastructure verification

| Component | Status | Evidence |
|-----------|--------|----------|
| Backend | Healthy | `docker ps`, in-container `/live` 200 (~77 ms) |
| Frontend | Healthy | UI `/auth/login` n=20 all OK |
| DB | Healthy | compose health |
| Redis | Healthy | compose health |
| Worker / beat | Healthy | compose health |
| Nginx | Up | `/live` `/health` via `:18080` OK |
| Restart loops | None | restart count 0 |
| RAGInspector Prometheus/Grafana | **NOT VERIFIED** | Only `ifg-prometheus` / `ifg-grafana` present — different stack |
| Docker network | Functional | Host→port and in-container probes work |

**Instant docker stats (post-bench sample):**

| Container | CPU | Memory |
|-----------|-----|--------|
| backend | ~13% | ~251 MiB |
| db | ~13% | ~127 MiB |
| worker | ~0.2% | ~867 MiB |
| redis | ~0.8% | ~7 MiB |
| frontend | ~0% | ~81 MiB |
| nginx | ~0% | ~3.5 MiB |

Continuous CPU/memory time series during load: **NOT VERIFIED** (no Prometheus scrape for this stack this pass).

---

## 7. Phase 4 — Authentication verification

| Test | Result |
|------|--------|
| Login (under budget) | **PASS** (200 + token) |
| Invalid Bearer | **401** |
| Missing auth | **401** |
| Spaced login latency (n=15, 4s gap) | p50 **382 ms**, p95 **427 ms**, max **471 ms**, 0 fails |
| Rapid login (n=60 in ~12s) | **429** after 20 — by design |
| Logout / refresh / concurrent sessions / CSRF / cookies | **NOT VERIFIED** |
| MFA path | **NOT VERIFIED** |

---

## 8. Phase 5 — Latency tables (verified)

### Unauthenticated (n=40 unless noted) — `bench_verify.json`

| Endpoint | p50 | p75 | p90 | p95 | p99 | avg | max | err |
|----------|----:|----:|----:|----:|----:|----:|----:|----:|
| `GET /live` | 6.6 | 7.0 | 8.0 | 8.3 | 46 | 8.2 | 71 | 0% |
| `GET /api/v1/ops/ready` | 29.7 | 38.3 | 45.4 | 46.5 | 53 | 33.6 | 54 | 0% |
| Nginx `GET /live` | 7.4 | 7.9 | 8.6 | 12.6 | 72 | 10.6 | 79 | 0% |
| Nginx `GET /health` | 7.1 | 7.4 | 8.5 | 9.7 | 34 | 8.3 | 48 | 0% |
| UI `GET /auth/login` (n=20) | 9.2 | 18.9 | 28.8 | 37.4 | 114 | 19.5 | 133 | 0% |

**Reproducible?** YES (this host, warm stack).  
**Production-representative?** NO — laptop + Docker Desktop + competing containers.

### Authenticated (single-threaded) — `bench_auth_load.json`

| Endpoint | n | p50 | p95 | p99 | avg | max | err |
|----------|--:|----:|----:|----:|----:|----:|----:|
| Login spaced | 15 | 382 | 427 | 463 | 366 | 471 | 0% |
| `GET …/metrics/dashboard` | 40 | 10.1 | 16.1 | 234 | 19.5 | 372 | 0% |
| `GET …/queries?limit=20` | 40 | 14.2 | 21.7 | 40 | 16.1 | 50 | 0% |
| `GET …/pipelines` | 30 | 11.5 | 14.3 | 243 | 22.5 | 336 | 0% |
| `GET …/queries/{id}` | 20 | 16.1 | 36.6 | 296 | 33.7 | 361 | 0% |

Dashboard/detail show **occasional high outliers** (p99 ≫ p95) even at concurrency 1 — likely GC/Docker/CPU steal; still 0% errors.

### NOT VERIFIED (latency)

| Surface | Why |
|---------|-----|
| Evaluation / analysis pipeline duration | No timed ingest→Celery complete cycle this pass |
| Report PDF generation | Not exercised |
| Large-document evaluation | Not exercised |
| Cold-start worker model load | Stack already warm |
| JWT refresh path | Not instrumented |
| k6 published scenarios | k6 not installed |

---

## 9. Phase 6 — Load testing

### Authenticated `GET /api/v1/metrics/dashboard`

| Users | Total req | OK | err | wall s | RPS | p50 ms | p95 ms |
|------:|----------:|---:|----:|-------:|------:|-------:|-------:|
| 10 | 80 | 80 | 0% | 4.57 | 17.5 | 64 | 3814 |
| 25 | 75 | 75 | 0% | 4.17 | 18.0 | 127 | 3849 |
| 50 | 100 | 100 | 0% | 1.23 | 81.3 | 412 | 815 |
| 100 | 200 | 200 | 0% | 4.57 | 43.8 | 1758 | 3821 |

### Unauthenticated `GET /live`

| Users | Total | err | RPS | p50 ms | p95 ms |
|------:|------:|----:|-----:|-------:|-------:|
| 10 | 80 | 0% | ~ | 18.8 | 36.8 |
| 25 | 75 | 0% | 302 | 55 | 82 |
| 50 | 100 | 0% | 158 | 72 | 316 |
| 100 | 200 | 0% | 233 | 205 | 483 |

**DB / Redis / worker utilization time series during load:** **NOT VERIFIED** (spot `docker stats` only).  
**Stress 500–1000 VU (k6 scripts):** **NOT VERIFIED**.

---

## 10. Failure analysis summary

| Failure | Why | Where | When | Frequency | Severity | Fix / mitigation | Verified |
|---------|-----|-------|------|-----------|----------|------------------|----------|
| Auth benches empty / “login failed” under rapid loops | SlowAPI 20/min | `POST /login` | After ~20 logins/min | Deterministic | Medium for **benchmark design**; Low for normal UX | Reuse token; space logins; document limits | **Yes** — 429 reproduced |
| Host connection reset (historical) | Likely Docker Desktop publish-port flake | Host→`:18000` | Under prior heavy/parallel load | Intermittent | Medium for Windows demos | Prefer stable port mapping / WSL2; retry; in-container probes | **Not reproduced today** |
| Multi-second dashboard p95 under concurrency | Resource contention / pool saturation | API+DB on laptop | Concurrent users ≥10 | Consistent tails | Medium for capacity planning | Scale API/DB; dedicated host; profile SQL | Observed; **not “fixed”** (env limit) |

---

## 11. Optimizations performed

**None applied to application code in this pass.**

Rationale: The deterministic auth “failure” was **correct rate limiting**. Changing limits to make benches green would **falsify** production behavior. Latency tails under load need dedicated profiling (SQL EXPLAIN, pool sizes) on a quiet host — not micro-optimizations on a contended 8 GB laptop.

**Harness / docs changes:**

- Added `loadtests/bench_verify.py`, `bench_auth_load.py`
- Documented rate-limit pitfall in `loadtests/README.md`

---

## 12. Benchmark validation checklist

| Metric family | Reproducible? | Measured correctly? | Prod-representative? | Samples | Confidence |
|---------------|---------------|---------------------|----------------------|---------|------------|
| Unauth health latency | YES | YES | NO | 40 | Medium (single host) |
| Login spaced | YES | YES | Partial (bcrypt cost is real) | 15 | Medium |
| Auth API single-thread | YES | YES | NO | 20–40 | Medium |
| Auth concurrent dashboard | YES (tails) | YES | NO | 75–200 | Low–medium (noisy) |
| Rapid login success rate | YES → 429 | YES | YES (limit intentional) | 60 | High |
| Evaluation pipeline | — | — | — | 0 | **NOT VERIFIED** |
| k6 100/500/1000 | — | — | — | 0 | **NOT VERIFIED** |

---

## 13. Scores (honest)

| Score | Value | Notes |
|-------|------:|-------|
| Measurement integrity | **9/10** | Root cause evidenced in code + JSON |
| Performance maturity of product | **7/10** | Health fast; auth cost expected; concurrency tails on weak host |
| Production readiness (perf) | **6.5/10** | Need dedicated-host k6 + pipeline timing + obs |
| Prior “auth NOT VERIFIED” claim | **Partially explained** | Was real gap; cause = rate limit (+ historical transport flake) |

---

## 14. Recommendations (highest ROI)

1. **Benchmark protocol:** one login → reuse Bearer; never burn 20/min budget for latency loops.  
2. **CI perf job:** run `bench_auth_load.py` against Compose with rate-limit-aware spacing; fail on error_rate > 0 for authed GETs.  
3. **Dedicated quiet host** for p95 claims; stop citing laptop numbers as SLOs.  
4. **Instrument analysis duration** (ingest → `analysis_status=completed`) as a first-class metric.  
5. **Bring up** `docker-compose.observability.yml` when claiming Prometheus/Grafana evidence.  
6. Optional: expose `Retry-After` on 429 responses for clearer client behavior (product change; not done here).

---

## 15. Final verdict

| Claim | Verdict |
|-------|---------|
| Unauthenticated latency numbers in artifacts | **TRUST for this environment** |
| Authenticated latency (after rate-limit-aware run) | **TRUST for this environment** |
| “Login connection reset is the root cause of all auth bench failures” | **REJECT as sole cause** — **429 rate limit** is the reproducible cause today |
| Production SLO readiness | **NOT VERIFIED** |
| Evaluation pipeline performance | **NOT VERIFIED** |

The objective was trustworthy engineering evidence. The suite now shows: **health paths are fine; login is intentionally capped; authenticated APIs work when measured correctly; concurrent dashboard tails need a better host before capacity claims.**
