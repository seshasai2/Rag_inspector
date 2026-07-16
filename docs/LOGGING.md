# Structured logging & request IDs (Phase 8.3)

## Behavior

- API uses **structlog**. `ENVIRONMENT=production` → JSON lines; otherwise console.
- Log level via `LOG_LEVEL` (default `INFO`); retention guidance via `LOG_RETENTION_DAYS` (default 30).
- Every HTTP request binds and echoes:
  - **`X-Request-ID`** (client-supplied if safe, else UUID)
  - **`X-Correlation-ID`** (defaults to request id)
  - **`X-Trace-ID`** (minted `trc_…` when absent)
- Failures also mint **`error_id`** (`err_…`) into structured logs.
- Access log line: `request` with `method`, `path`, `status_code`, `duration_ms`, ids
- Nginx forwards / mints `X-Request-ID` to the backend (`nginx.conf` / `nginx.tls.conf`)
- Celery workers call `setup_logging()` on process start and bind `celery_task_id` (+ inbound `request_id` when enqueue carried it)
- Audit events go to the `audit_logs` table (application audit trail)

## Trace a request

1. Note `X-Request-ID` / `X-Trace-ID` from the browser / `curl -i` response.
2. Grep API / worker container logs for that id:

```bash
docker compose logs backend | findstr /i "YOUR-REQUEST-ID"
docker compose logs celery_worker | findstr /i "YOUR-REQUEST-ID"
```

## Retention

| Class | Recommendation | Mechanism |
|-------|----------------|-----------|
| Operational logs | 14–30 days (`LOG_RETENTION_DAYS`) | Cluster log shipper / Compose `max-size`×`max-file` |
| Security / audit | 90–365 days (legal) | Separate sink; do not rely on container local disk |
| Debug traces | 7 days | Sampling; drop PII |
| Docker json-file | Daily-ish rotation by size | `max-size: 10m`, `max-file: 5` (~50MB/service) |

Never use unbounded host volume logging.

## Metrics retention

| Class | Resolution | Retention |
|-------|------------|-----------|
| High-resolution ops (CPU, latency, backlog) | 15–30s scrape | 15 days (Prometheus TSDB) |
| Long-term capacity | 5m rollups | 90 days |
| Business metrics (traces/day) | 1h | 1+ year in warehouse / billing DB |

## Related

- [DEPLOYMENT.md](DEPLOYMENT.md)
- [COMPOSE_PROD.md](COMPOSE_PROD.md)
- [engineering/MONITORING.md](engineering/MONITORING.md)
- [KUBERNETES.md](KUBERNETES.md)
