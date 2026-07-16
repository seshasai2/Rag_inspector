# Dashboard metrics Redis cache (Phase 6.5)

`GET /api/v1/metrics/dashboard` and related aggregate endpoints can reuse a short Redis TTL so repeated dashboard polls skip heavy SQL.

## Config

| Variable | Default | Meaning |
|----------|---------|---------|
| `DASHBOARD_METRICS_CACHE_ENABLED` | `true` | Master switch |
| `DASHBOARD_METRICS_CACHE_TTL_SECONDS` | `30` | Soft freshness window; `0` disables |
| `REDIS_URL` | (required for hits) | Same Redis as Celery / health checks |

Disable entirely:

```bash
DASHBOARD_METRICS_CACHE_ENABLED=false
# or
DASHBOARD_METRICS_CACHE_TTL_SECONDS=0
```

## Behavior

- **Fail-open:** if Redis is unreachable, every request recomputes from Postgres (same as uncached).
- **Keys** are scoped by user id + optional `pipeline_id` (+ metric/days for chart endpoints).
- Responses include `X-Cache: hit | miss | bypass` for measurement.

Cached routes:

- `/metrics/dashboard`
- `/metrics/timeseries`
- `/metrics/failure-distribution`
- `/metrics/latency-breakdown`
- `/metrics/bm25-comparison`

Code: `app/core/redis_cache.py`, `app/services/dashboard_cache.py`.

## Latency notes (measurable)

Dashboard rebuilds typically run **~6–10 SQL statements** (Phase 6.2). A cache **hit** avoids that work and returns deserialized JSON only.

Local unit measurement (`tests/unit/test_dashboard_cache.py`) with a 40 ms artificial factory:

| Path | Observed |
|------|----------|
| Miss (recompute) | ≥ ~40 ms (factory cost) |
| Hit (Redis fake) | ≪ miss / 2, usually &lt; 20 ms |

How to measure in a running stack:

1. Warm: `curl -D - -H "Authorization: Bearer $TOKEN" "$API/api/v1/metrics/dashboard"` → expect `X-Cache: miss`.
2. Immediate repeat → expect `X-Cache: hit` and lower server time (`curl -w '%{time_total}\n'`).
3. Wait &gt; TTL (default 30 s) → miss again.

Stale window is intentional: dashboards tolerate ~30 s lag; ingest does not invalidate keys (TTL only).

## Ops checklist

1. Keep Redis healthy (`GET /ops/health` redis check).
2. Start with 30 s TTL; raise if DB load is high and freshness allows.
3. Set `DASHBOARD_METRICS_CACHE_ENABLED=false` in environments that need always-fresh demos.

## Related

- Cold start / ML: `docs/COLD_START.md`
- Indexes: `docs/INDEXES.md`
