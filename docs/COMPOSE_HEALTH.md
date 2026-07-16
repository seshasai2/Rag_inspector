# Compose healthchecks (Phase 7.2 / 8.4)

`docker compose up` waits on **healthy** dependencies before starting dependents.

## Liveness vs readiness

| Probe | Endpoint | Meaning |
|-------|----------|---------|
| **Liveness** | `GET /health` or `GET /live` | Process is up (always 200 if the API process responds) |
| **Readiness** | `GET /api/v1/ops/ready` | DB + Redis OK; **503** when degraded |

Compose can attach **one** healthcheck per service. Backend uses **readiness** so an orchestrator restarts (or stops routing to) the container when dependencies fail. For Kubernetes, set:

- `livenessProbe` → `/health` or `/live`
- `readinessProbe` → `/api/v1/ops/ready`

## Probes

| Service | Healthcheck | Notes |
|---------|-------------|--------|
| `db` | `pg_isready` | Existing |
| `redis` | `redis-cli ping` | Existing |
| `backend` | `GET /api/v1/ops/ready` (curl) | **503** if DB or Redis fail; liveness-only is `GET /health` / `/live` |
| `frontend` | Node `fetch` to `/` | No curl in Alpine image |
| `celery_worker` | `celery inspect ping` → `pong` | `start_period: 90s` (dev) / `120s` (prod) for ML warm |
| `postgres_backup` | none | Sidecar loop; depends on `db` healthy only |

## Dependency graph

```
db (healthy) ─┬─► backend (healthy) ─┬─► frontend (healthy) ─► nginx
redis (healthy)┘                      └─► (nginx also waits on backend)

db + redis (healthy) ─► celery_worker (healthy), celery_beat
db (healthy) ─► postgres_backup
```

`depends_on: condition: service_healthy` is set for backend ← db/redis, frontend ← backend, nginx ← backend+frontend, workers/beat ← db/redis. `postgres_backup` waits on **db** only.

## Verify

```bash
docker compose config --quiet
docker compose up -d
docker compose ps   # HEALTHY on backend, frontend, celery_worker
curl -fsS http://localhost:8000/api/v1/ops/ready
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/live
```

Unhealthy backend: Compose marks the service unhealthy; dependents that require `service_healthy` will not start / stay blocked until it recovers (or the container is restarted per `restart:` policy).

## Related

- Worker concurrency: [`WORKER.md`](WORKER.md)
- Deployment checklist: [`DEPLOYMENT.md`](DEPLOYMENT.md)
- Prod compose: [`COMPOSE_PROD.md`](COMPOSE_PROD.md)
