# Performance

Measured baselines for RAGInspector. These numbers come from a **dev laptop** (Windows Docker Desktop, ~8 GB RAM, competing containers). They are **not** contractual SLOs. Re-run `loadtests/` against your environment before capacity planning.

**Artifacts:** `loadtests/artifacts/` · harnesses in `loadtests/bench_verify.py`, `bench_auth_load.py` · scripts under `loadtests/k6/` and Locust.

---

## Environment class

| Item | Typical freeze / verification host |
|------|-------------------------------------|
| Hardware | Laptop-class (≈12 logical CPUs, ≈8 GB RAM) |
| Runtime | Docker Desktop + Compose verify-ports |
| App ports | API `:18000`, UI `:13000`, Nginx `:18080` |
| Observability | Optional `docker-compose.observability.yml` |

Multi-second authenticated p95 under 100 concurrent VUs on this class of host is usually **contention**, not a single-code-path bug. Validate on quiet dedicated hardware before blaming the app.

---

## Rate limiting (authenticated benches)

Systematic login failures under rapid loops are almost always **HTTP 429**, not JWT bugs.

| Limit | Value | Location |
|-------|-------|----------|
| Login (API) | `20/minute` | `AUTH_LOGIN_LIMIT` in `backend/app/core/rate_limit.py` |
| Nginx auth zone | ~5/min (edge) | `nginx/nginx.conf` |

Evidence shape: attempts 1–19 → 200; attempt 20 → `{"error":"Rate limit exceeded: 20 per 1 minute"}`. Space logins when collecting authenticated latency.

---

## Latency (verified samples)

| Surface | p50 | p95 | Notes |
|---------|----:|----:|-------|
| `GET /live` | ~6 ms | ~8–40 ms | httpx / k6 |
| `GET /api/v1/ops/ready` | ~30 ms | ~47–134 ms | Touches DB + Redis |
| Login (spaced) | ~350–400 ms | ~430 ms | bcrypt-dominated |
| Dashboard (auth, Redis hit) | ~14–17 ms | ~16–60 ms | `X-Cache: hit` |
| JWT refresh | ~35 ms | ~194 ms | n≈8 |
| Ingest → analysis `completed` | — | — | ≈2.2 s ingest + ≈7.7 s worker wait (single sample) |

### k6 smoke (10 VU, 1 minute)

| Trend | p95 (typical) |
|-------|--------------:|
| `http_req_duration` | 64–75 ms |
| `/live` | ~40 ms |
| `/api/v1/ops/ready` | 102–134 ms |

### Locust (10 users, 60 s)

≈50 aggregated requests, **0%** failures in the recorded smoke; login averages hundreds of ms (bcrypt).

### Concurrent dashboard load

At 100 VU on the laptop host: **0%** HTTP errors observed, but **p95 multi-second**. Treat as capacity/hardware, not auth failure.

---

## Soak (30 minutes)

| Metric | Result |
|--------|--------|
| Combined live + dashboard probes | ~0.1% error (timeouts / protocol under host load) |
| Container restarts | 0 |
| Backend RSS samples | ~239 → ~504 MiB — growth observed; **leak not proven** |

---

## Known bottlenecks

1. **Analysis workers** — local NLI / embeddings dominate RAM; keep concurrency 1–2 and scale horizontally ([WORKER.md](../WORKER.md), [COLD_START.md](../COLD_START.md)).
2. **Login rate limits** — intentional; break naive bench scripts.
3. **Dashboard aggregates** — mitigated by Redis TTL cache ([DASHBOARD_CACHE.md](../DASHBOARD_CACHE.md)); miss latency less often measured than hits.
4. **Windows Docker Desktop publish ports** — intermittent host↔container resets documented in ops notes; prefer in-network probes when collecting evidence.
5. **Prometheus scrape** — `/api/v1/ops/metrics` must return Prometheus plaintext (`PlainTextResponse`). JSON encoding breaks `up`.

---

## How to re-measure

```bash
# Health smoke (requires k6)
k6 run loadtests/k6/smoke.js

# Auth-aware harness (respects login budget)
python loadtests/bench_verify.py
python loadtests/bench_auth_load.py
```

Replace tables in this document with your observed results after worker/API replica changes. Scaling notes: [SCALING.md](SCALING.md).
