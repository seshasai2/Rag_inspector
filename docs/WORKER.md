# Celery worker concurrency & backlog (Phase 6.6)

Analysis runs on Celery (`run_analysis` → queue **`analysis`**). Beat/webhooks use queue **`celery`**. See `app/workers/celery_app.py`.

## Recommended process model

| Knob | Default / guidance | Why |
|------|--------------------|-----|
| `--concurrency` | **1–2** on analysis workers | Each process holds NLI + embedding weights (see [`COLD_START.md`](COLD_START.md)). High concurrency × ML ≈ OOM. |
| `worker_prefetch_multiplier` | **1** (set in code) | Long ML tasks; avoid hoarding messages on one worker. |
| `task_acks_late` | **true** | Lost workers re-queue in-flight analysis. |
| Horizontal scale | Prefer **more containers** at concurrency 1–2 | Better than one fat process when models dominate RAM. |
| Queues | Consume **`analysis,celery`** (or two workers) | Compose historically only listened to `analysis`; beat/webhook tasks sit forever otherwise. |

### Example commands

Local / Compose (matches `docker-compose.yml`):

```bash
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 -Q analysis,celery
```

Split roles (heavy ML vs light tasks):

```bash
# Analysis only — keep concurrency low
celery -A app.workers.celery_app worker -n analysis@%h --concurrency=1 -Q analysis

# Webhooks / beat tasks — can raise concurrency (no ML warm required)
celery -A app.workers.celery_app worker -n default@%h --concurrency=4 -Q celery \
  WARM_ML_MODELS_ON_WORKER_START=false   # via env
```

Beat (scheduler only — does not consume queues):

```bash
celery -A app.workers.celery_app beat --loglevel=info
```

## Sizing rules of thumb

1. **RAM:** ≈ (embedding + NLI) × `--concurrency` per container, plus Postgres/Redis overhead on the host.
2. **CPU:** analysis is often model-bound; 2 concurrent tasks on a 4-vCPU box is a reasonable start.
3. **Throughput:** if `/ops/backlog` shows growing `celery_queue_depths.analysis` or `analysis_jobs.pending`, add another analysis worker replica before raising concurrency past 2.
4. **Warm models:** keep `WARM_ML_MODELS_ON_WORKER_START=true` on analysis workers so cold start is not paid per task.

## Backlog metrics

| Endpoint | Format | Use |
|----------|--------|-----|
| `GET /api/v1/ops/backlog` | JSON | Human / scripts: Redis LLEN per queue, `analysis_jobs` by status, traces `pending`/`analyzing`/`failed` |
| `GET /api/v1/ops/metrics` | Prometheus text | Uptime, build info, **HTTP RED** (`raginspector_http_requests_total`, `raginspector_http_request_duration_seconds_*`), Celery queue depth, analysis backlog gauges |

Code: `app/services/worker_backlog.py`.

### What “healthy” looks like

- `celery_messages_waiting` near **0** under steady load.
- `analysis_jobs.pending` not climbing for minutes while workers are up.
- Spikes after ingest bursts that drain within a few minutes are normal.

### Alert ideas

- `raginspector_analysis_backlog > N` for 10+ minutes
- `raginspector_celery_queue_depth{queue="analysis"}` growing while worker replicas = 0 / crash-looping
- Redis check on `/ops/ready` not `ok`

## Ops checklist

1. Workers listen to every queue that receives tasks (`analysis` + `celery`, or dedicated consumers).
2. Start with `--concurrency=2`; raise only after measuring RAM and backlog drain rate.
3. Scrape `/api/v1/ops/metrics` or poll `/api/v1/ops/backlog`.
4. On Redis/Celery outages, ingest still stores traces as failed/pending — use `POST /api/v1/queries/{id}/reanalyze` after recovery.

## Related

- Deployment: [`DEPLOYMENT.md`](DEPLOYMENT.md)
- ML cold start: [`COLD_START.md`](COLD_START.md)
- Dashboard Redis TTL cache (API, not workers): [`DASHBOARD_CACHE.md`](DASHBOARD_CACHE.md)
