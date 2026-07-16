# Operations

Day-2 operations for RAGInspector. Deeper runbooks live in `docs/RUNBOOKS.md`.

## Health signals

| Endpoint | Meaning |
|----------|---------|
| `GET /live` | Process up |
| `GET /health` | Alias of live with version |
| `GET /api/v1/ops/ready` | DB + Redis OK → 200; else 503 degraded |
| `GET /api/v1/ops/backlog` | Queue depths + job counts |
| `GET /api/v1/ops/metrics` | Prometheus gauges |

## Routine tasks

1. **Migrations** — `make migrate` / Alembic upgrade before new API pods take traffic.
2. **Seed (non-prod)** — `make seed` for demos only.
3. **Logs** — `make logs`; filter by `request_id`.
4. **Workers** — confirm `-Q analysis,celery`; concurrency 1–2 analysis.
5. **Backups** — follow [BACKUP.md](../BACKUP.md); test restore quarterly.
6. **Certificates** — ingress TLS rotation ([TLS.md](../TLS.md)).
7. **Secrets** — rotate `SECRET_KEY` only with coordinated re-login; rotate API keys via API.

## Incident quick path

1. Check `/ops/ready` and Compose/K8s pod status.
2. If Redis down: ingest may mark failed — repair Redis, reanalyze.
3. If Postgres down: API degraded — failover / restore.
4. If backlog climbs: scale analysis workers, not API alone.
5. Capture timestamps + request ids for postmortem ([INCIDENT_RESPONSE.md](../INCIDENT_RESPONSE.md)).

## Deploy

- Dev: `make bootstrap` / `make up`
- Prod compose: `make up-prod`
- Helm: [HELM.md](../HELM.md)
- Validate: `make validate-release`

## On-call cheat sheet

| Alert | First action |
|-------|--------------|
| Ready failing | Check Postgres then Redis |
| Analysis backlog | Scale workers; inspect OOM kills |
| Error rate API | Trace logs by path; recent deploy? |
| Hallucination Slack storm | Confirm real spike vs ingest test flood |

Related: [SRE_CHECKLIST.md](../SRE_CHECKLIST.md), [MONITORING.md](MONITORING.md).
