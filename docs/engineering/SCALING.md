# Scaling

How RAGInspector scales horizontally. Prefer evidence from `/ops/backlog` and loadtests over guesswork.

## API (FastAPI / Uvicorn)

| Lever | Guidance |
|-------|----------|
| Replicas | Scale on CPU / RPS / p95 latency |
| DB pool | Size pools per replica; avoid stampeding Postgres |
| Cache | Dashboard Redis TTL reduces repeat aggregate load |
| Rate limits | Protect auth/ingest under bot traffic |

Stateless API pods behind a load balancer; session state is JWT + DB.

## Workers

| Queue | Scale signal | Notes |
|-------|--------------|-------|
| `analysis` | queue depth, pending jobs | Concurrency **1–2**; scale replicas |
| `celery` | webhook lag, beat task delay | Higher concurrency OK |

Warm ML models imply RAM ≈ model set × concurrency per pod. See [WORKER.md](../WORKER.md), [COLD_START.md](../COLD_START.md).

## Data stores

| Store | Scale notes |
|-------|-------------|
| PostgreSQL | Vertical first; indexes from [INDEXES.md](../INDEXES.md); read replicas optional for reporting |
| Redis | Broker + cache; monitor memory and eviction; separate cache DB index if needed |

## Frontend

Next.js scales as static/SSR pods; cache aggressively at CDN for marketing routes. Dashboard remains dynamic against API.

## Autoscaling references

See [AUTOSCALING.md](../AUTOSCALING.md) for HPA sketches on analysis backlog and API CPU.

## Load verification

Re-run:

```bash
k6 run loadtests/k6/load_100.js
k6 run loadtests/k6/stress_1000.js
```

Record p50/p95/p99 into your environment’s capacity doc; [PERFORMANCE.md](PERFORMANCE.md) is a baseline only.

## Anti-patterns

- Raising analysis concurrency to 8 on one GPU-less node → OOM.
- Scaling API to fix stuck analyses → wrong knob.
- Single beat replica with HPA → duplicate schedules; keep beat at 1.
