# Performance Sanity (Phase 10)

Measure only — do not optimize unless a clear problem blocks demos.

## Checklist

| Check | Method | Healthy local ballpark | Problem if |
|-------|--------|------------------------|------------|
| API startup | Time until `/live` 200 after `compose up` | < 60s warm image | > 3 min repeatedly |
| Ready | `/ops/ready` latency | < 500 ms | > 2 s sustained |
| Login | `POST /auth/login` | < 1 s | > 3 s |
| Dashboard metrics | `GET /metrics/dashboard` after seed | < 2 s (cache cold) | > 5 s |
| Page load (UI) | DevTools LCP dashboard | < 3 s local | Blank > 10 s |
| Worker job | Reanalyze seeded small trace | < 2 min with warm models | Hang > 10 min |
| Memory (worker) | `docker stats` | Fits host; interview overlay lowers limits | OOM kill loops |
| CPU | `docker stats` during idle | Near 0% | Pegged 100% idle |
| DB | ready `database=ok` | — | repeated reconnect errors |

## Commands

```bash
curl -sS -o /dev/null -w "live:%{time_total}\n" http://localhost:8000/live
curl -sS -o /dev/null -w "ready:%{time_total}\n" http://localhost:8000/api/v1/ops/ready
docker stats --no-stream
```

Load tests (optional release): `loadtests/` (k6 / Locust) — see `loadtests/README.md`.

## Interview overlay

Use `docker-compose.interview.yml` on low-RAM machines; keep `WARM_ML_MODELS_ON_WORKER_START=false` and rely on **seeded** traces for the 10–15 min demo.
