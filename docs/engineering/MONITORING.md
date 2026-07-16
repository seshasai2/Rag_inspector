# Monitoring

Observable surfaces for RAGInspector using open-source stacks (Prometheus, Grafana, structlog). Overlay: `make up-obs`.

## Application metrics

| Source | Format | Contents |
|--------|--------|----------|
| `GET /api/v1/ops/metrics` | Prometheus text | Queue depths, analysis job gauges, backlog |
| `GET /api/v1/ops/backlog` | JSON | Human-readable depths and status counts |
| HTTP logs | structlog JSON | method, path, status, duration_ms, request_id |

Instrument additional business metrics carefully to avoid high-cardinality labels (no raw query text as labels).

## Golden signals

1. **Latency** — API p95 by route; analysis job duration histogram (logs or custom metrics).
2. **Traffic** — RPS on `/ingest/trace` and dashboard GETs.
3. **Errors** — 5xx rate; worker task failure rate.
4. **Saturation** — Redis memory, Postgres connections, Celery depth, pod CPU/RAM.

## Recommended alerts

| Condition | Severity |
|-----------|----------|
| `/ops/ready` failing 2m | page |
| `analysis` queue depth high 10m | ticket / page if SLO tight |
| API 5xx > 2% 5m | page |
| Worker OOMRestart loop | page |
| Disk on Postgres > 85% | ticket |

## Tracing & correlation

- Propagate `X-Request-ID` / `X-Correlation-ID` / `X-Trace-ID`.
- Optional Sentry init (`app/core/sentry_init.py`) when DSN configured — keep PII scrubbing on.

## Dashboards

Grafana starter assets live under `infra/` / observability compose. Panels to include:

- Request rate & latency
- Ready status
- Celery queue depth
- Analysis pending/running/failed
- Hallucination rate (business) from metrics API scrapes or scheduled SQL

## Synthetic checks

- Blackbox `/live` and `/ops/ready` from outside the cluster.
- Periodic k6 smoke in CI staging ([loadtests/README.md](../../loadtests/README.md)).

Related: [OPERATIONS.md](OPERATIONS.md), [LOGGING.md](../LOGGING.md), [WORKER.md](../WORKER.md).
