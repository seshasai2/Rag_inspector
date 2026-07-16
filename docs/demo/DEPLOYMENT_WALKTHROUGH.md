# Deployment walkthrough (demo)

How to bring up RAGInspector for a live demo and what to say about production.

## Local one-command path

```bash
cp .env.example .env   # set SECRET_KEY
make bootstrap         # build, up, migrate, health wait
make seed              # demo user + traces
```

Endpoints:

- UI http://localhost:3000  
- API http://localhost:8000  
- OpenAPI http://localhost:8000/docs  

## Health narrative

```bash
curl -s http://localhost:8000/live
curl -s http://localhost:8000/api/v1/ops/ready
```

Explain that `/live` is process liveness and `/ops/ready` checks Postgres + Redis (may return 503 degraded).

## Worker narrative

```bash
docker compose logs -f worker --tail=50
curl -s http://localhost:8000/api/v1/ops/backlog
```

Workers must consume `analysis,celery`. Concurrency 1–2 for ML. See [WORKER.md](../WORKER.md).

## Production-shaped path (talk track)

1. `make up-prod` or Helm chart under `infrastructure/` ([HELM.md](../HELM.md), [KUBERNETES.md](../KUBERNETES.md)).
2. Secrets via env / sealed secrets ([SECRETS.md](../SECRETS.md)).
3. TLS at ingress ([TLS.md](../TLS.md)).
4. Observability overlay: `make up-obs` ([MONITORING engineering doc](../engineering/MONITORING.md)).
5. Autoscaling on API RPS and analysis backlog ([AUTOSCALING.md](../AUTOSCALING.md)).

## Rollback / DR talking points

- Alembic migrations forward-only in demos; mention [BACKUP.md](../BACKUP.md) and [DISASTER_RECOVERY.md](../DISASTER_RECOVERY.md) for real ops.
- Image tags pinned in prod compose; SBOM via `make sbom`.

## Checklist before audience arrives

| Check | OK |
|-------|----|
| `make ps` all healthy | |
| Demo login works | |
| At least one grounded query | |
| Worker log shows `run_analysis` completes | |
| `/docs` reachable (non-prod) | |

Related: [DEPLOYMENT.md](../DEPLOYMENT.md), [10-deployment-diagram.md](../architecture/10-deployment-diagram.md).
