# Kubernetes deployment

Cloud-agnostic deployment for AKS, EKS, GKE, on-prem Kubernetes, and OpenShift.
Primary install path: **Helm** (`infrastructure/helm/raginspector`).

## Architecture (cluster)

| Workload | Role | Public? |
|----------|------|---------|
| backend | FastAPI API | via Ingress only |
| frontend | Next.js UI | via Ingress only |
| worker | Celery (`analysis`, `celery`) | internal |
| beat | Celery Beat (singleton) | internal |
| postgres | **Dev only** (`postgresql.enabled`) | ClusterIP |
| redis | Optional in-cluster | ClusterIP |
| prometheus / grafana | Optional lab stack | ClusterIP |

Production uses **managed Postgres + Redis**. Do not run chart Postgres in production.

## Health probes

| Probe | Backend | Meaning |
|-------|---------|---------|
| Startup | `GET /live` | Process started |
| Liveness | `GET /live` | Restart if process dead |
| Readiness | `GET /api/v1/ops/ready` | **Fails if Postgres or Redis unavailable** |

Workers: Celery `inspect ping` liveness (ML warm-up via `initialDelaySeconds`).

## Quick install (staging/prod)

```bash
# 1) Pre-create secrets (docs/SECRETS.md)
kubectl create namespace raginspector
kubectl -n raginspector create secret generic raginspector-secrets \
  --from-literal=SECRET_KEY='…' \
  --from-literal=DATABASE_URL='postgresql+asyncpg://…' \
  --from-literal=DATABASE_SYNC_URL='postgresql://…' \
  --from-literal=REDIS_URL='redis://:…@…:6379/0' \
  --from-literal=OPS_SHARED_TOKEN='…'

# 2) Install
helm upgrade --install raginspector ./infrastructure/helm/raginspector \
  -f ./infrastructure/helm/raginspector/values-production.yaml \
  --namespace raginspector

# 3) Validate
API_URL=https://api.example.com FRONTEND_URL=https://app.example.com \
  python scripts/validate_release.py
```

## Dev cluster (in-cluster DB)

```bash
helm upgrade --install raginspector ./infrastructure/helm/raginspector \
  -f ./infrastructure/helm/raginspector/values-development.yaml \
  --namespace raginspector-dev --create-namespace
```

## Resource assumptions

Documented in `docs/AUTOSCALING.md`. Summary:

- API: 250m–2 CPU, 512Mi–2Gi; HPA on CPU/memory
- Workers: 500m–4 CPU, 2–8Gi (sentence-transformers); HPA or KEDA on queue depth
- Beat: single replica (Recreate strategy)

## Security posture

- Non-root uid 10001, drop ALL capabilities, read-only root FS + emptyDir for `/tmp` and cache
- NetworkPolicies default-deny + least-privilege egress
- TLS via Ingress (`ssl-redirect`); app HSTS when `ENVIRONMENT=production`
- Secrets never in ConfigMaps

## OpenShift notes

- Chart sets `runAsNonRoot` / `seccompProfile`; adjust `runAsUser` if SCC disallows 10001
- Prefer `Route` equivalent or OpenShift Ingress controller; set `ingress.className` accordingly

## Related

- `docs/HELM.md` — values reference
- `docs/SECRETS.md` — rotation + External Secrets
- `docs/RUNBOOKS.md` — day-2 operations
- `docs/TLS.md` — Compose TLS; Ingress TLS for Kubernetes
