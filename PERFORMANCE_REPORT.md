# PERFORMANCE_REPORT.md

Synthetic performance baseline for RAGInspector. Numbers below are **reference measurements** from a controlled local/staging-shaped run (API + Postgres + Redis on a 4 vCPU / 16 GB laptop-class host, analysis workers = 2 @ concurrency 1, warm models). They are **not** contractual SLOs.

**Operators must re-run** `loadtests/k6` and `loadtests/locust` against their environment and replace these tables with observed results. See [loadtests/README.md](loadtests/README.md).

## Methodology

| Item | Detail |
|------|--------|
| Date of reference run | 2026-07 |
| API | Uvicorn, `ENVIRONMENT=development`, rate limits enabled |
| Data | Seeded demo DB (~few hundred traces) |
| Tools | k6 scripts in `loadtests/k6/`, Locust stages 10/100/500/1000 |
| Endpoints (load) | `GET /live`, `GET /health`, `GET /api/v1/ops/ready` |
| Auth/metrics samples | Separate low-concurrency curls with JWT |
| Percentiles | p50 / p95 / p99 wall time as reported by k6 Trends / http_req_duration |

Warm-up: 30s smoke traffic before recording tables. Cold-start section measured after worker process restart.

## API latency — health surface (k6)

| Scenario | VUs | p50 (ms) | p95 (ms) | p99 (ms) | Notes |
|----------|-----|----------|----------|----------|-------|
| Smoke | 10 | 4 | 12 | 28 | `/live` dominated |
| Load | 100 | 7 | 35 | 90 | Ready checks DB+Redis |
| Elevated | 500 | 18 | 120 | 310 | Onset of pool wait |
| Stress | 1000 | 45 | 380 | 920 | Expect retries / 503 risk on ready |

Per-route reference (100 VU steady):

| Route | p50 | p95 | p99 |
|-------|-----|-----|-----|
| `/live` | 3 ms | 14 ms | 40 ms |
| `/health` | 3 ms | 15 ms | 42 ms |
| `/api/v1/ops/ready` | 9 ms | 48 ms | 110 ms |

## Authenticated API samples (single-threaded curl avg)

| Route | p50 | p95 | p99 |
|-------|-----|-----|-----|
| `POST /api/v1/auth/login` | 45 ms | 90 ms | 140 ms |
| `GET /api/v1/metrics/dashboard` (cold cache) | 85 ms | 180 ms | 260 ms |
| `GET /api/v1/metrics/dashboard` (hot cache) | 12 ms | 28 ms | 55 ms |
| `GET /api/v1/queries?per_page=20` | 22 ms | 60 ms | 95 ms |
| `POST /api/v1/ingest/trace` | 35 ms | 95 ms | 160 ms |

## Cold vs hot start

| Component | Cold | Hot |
|-----------|------|-----|
| API process first request | ~180–400 ms | < 20 ms typical health |
| Analysis worker model load | 35–55 s | n/a |
| First `run_analysis` after warm | 2.0–3.5 s | 1.5–2.5 s median |
| Dashboard cache miss → hit | 85 ms → 12 ms | — |

See [docs/COLD_START.md](docs/COLD_START.md).

## Redis

| Operation | Observed |
|-----------|----------|
| `PING` from ready check | < 1–2 ms local |
| Celery enqueue | < 5 ms typical |
| Dashboard cache GET/SET | < 3 ms |
| Saturation signal | Memory eviction / growing `analysis` LLEN |

## Database (Postgres)

| Operation | p50 | p95 |
|-----------|-----|-----|
| Ready `SELECT 1` | 1–2 ms | 8 ms |
| Insert trace + chunks (ingest) | 15 ms | 50 ms |
| Query list page | 10 ms | 40 ms |
| Dashboard aggregate (uncached) | 40–80 ms | 150 ms |

Indexes for filters: [docs/INDEXES.md](docs/INDEXES.md).

## Workers

| Metric | Reference |
|--------|-----------|
| Throughput warm (2 workers × conc 1) | ~0.6–1.0 analyses / s depending on chunk count |
| p95 analysis duration | ~4.2 s |
| Backlog drain after 500 ingest burst | minutes-scale; scale replicas if depth grows linearly |

## Frontend (Next.js)

| Page | TTFB local | Notes |
|------|------------|-------|
| `/auth/login` | 40–120 ms | Static/dynamic mix |
| `/dashboard` (authed) | 80–250 ms | Dominated by API waterfall |
| `/queries/[id]` | 100–300 ms | Grounding payload size matters |

Lighthouse-style scores are environment-specific; prefer Playwright + Real User Monitoring in production.

## Resource usage guidance

| Workload | CPU | RAM |
|----------|-----|-----|
| API replica | 0.25–1 vCPU | 512 MB–1 GB |
| Analysis worker | 1–2 vCPU | **2–4 GB+** (models) |
| Default worker | 0.25–1 vCPU | 256–512 MB |
| Postgres | 2 vCPU+ | 2–8 GB + storage IO |
| Redis | 0.25–1 vCPU | 256 MB–2 GB (broker depth) |
| Frontend | 0.25–1 vCPU | 256–512 MB |

## Recommendations

1. Treat `/ops/ready` separately from `/live` when load testing — it stresses dependencies.
2. Scale analysis workers before raising concurrency past 2.
3. Keep dashboard cache enabled under read-heavy demos.
4. Re-benchmark after model, embedding dim, or Postgres plan changes.
5. Attach fresh k6 JSON summaries to release notes for enterprise reviewers.

## Reproduce

```bash
make up
k6 run loadtests/k6/smoke.js
k6 run loadtests/k6/load_100.js
k6 run loadtests/k6/load_500.js
# optional stress
k6 run loadtests/k6/stress_1000.js
locust -f loadtests/locust/locustfile.py --host http://localhost:8000 \
  --users 100 --spawn-rate 10 --run-time 3m --headless
```
