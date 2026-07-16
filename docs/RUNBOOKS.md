# Operations runbooks

Commands assume Helm release `raginspector` in namespace `raginspector` unless noted.

## Starting services

```bash
helm upgrade --install raginspector ./infrastructure/helm/raginspector \
  -f ./infrastructure/helm/raginspector/values-production.yaml -n raginspector
kubectl -n raginspector get pods -w
```

Expected: Deployments Available; migrate + validate Jobs Complete.
Verify: `python scripts/validate_release.py` with `API_URL` / `FRONTEND_URL`.

Compose: `make bootstrap` or `make up-prod`.

## Stopping services

```bash
helm uninstall raginspector -n raginspector
# PVCs may remain — delete deliberately:
kubectl -n raginspector delete pvc --all
```

Compose: `make down`.

## Scaling

```bash
kubectl -n raginspector scale deploy/raginspector-backend --replicas=5
# Prefer HPA: edit values backend.autoscaling.maxReplicas then helm upgrade
kubectl -n raginspector get hpa
```

Expected: pods Ready; PDB not violated (`kubectl get pdb`).

## Restarting workers

```bash
kubectl -n raginspector rollout restart deploy/raginspector-worker
kubectl -n raginspector rollout status deploy/raginspector-worker
```

Expected: Celery ping succeeds; backlog decreases (`/api/v1/ops/backlog` with ops token).

## Queue backlogs

1. `curl -H "X-Ops-Token: $OPS_SHARED_TOKEN" $API/api/v1/ops/backlog`
2. Scale workers up (HPA/KEDA or manual).
3. Check worker logs for OOM/error: `kubectl logs -l app.kubernetes.io/component=worker --tail=200`
4. Verify Redis connectivity via `/ops/ready`.
5. See `docs/WORKER.md`.

## Database maintenance

- Prefer managed maintenance windows.
- Migrations: automatic Helm hook; manual:
  `kubectl -n raginspector run migrate --rm -it --image=$BACKEND_IMAGE -- alembic upgrade head`
  (with envFrom secret/config).
- Vacuum/analyze: provider tooling; never run destructive ops without backup verify.

## Redis maintenance

- Failover: managed Redis automatic; API readiness will 503 until Redis returns.
- Flush: **avoid** in production (broker + cache). If required, drain workers first.

## Log inspection

```bash
kubectl -n raginspector logs -l app.kubernetes.io/component=backend --tail=100 -f
# Filter request id from JSON logs — see docs/LOGGING.md
```

Compose: `make logs`.

Retention: cluster log shipper (Loki/CloudWatch/Stackdriver) — recommend **30d** operational, **90–365d** legal if required. Container json-file limits in Compose: 10m × 5.

## Performance investigation

1. Grafana/Prometheus: API latency, backlog, CPU/memory HPA events.
2. `/ops/ready` soft fields for backlog counts.
3. DB slow queries / connection saturation.
4. Worker concurrency vs RAM (`docs/COLD_START.md`).

## Incident response

Severity + contact path: `docs/INCIDENT_RESPONSE.md`.
First checks: ready probe, Redis, Postgres, worker pods, recent deploy.

## Emergency rollback

```bash
helm history raginspector -n raginspector
helm rollback raginspector <REVISION> -n raginspector
# If schema incompatible: restore DB from PITR/dump BEFORE/WITH app rollback (docs/DISASTER_RECOVERY.md)
python scripts/validate_release.py
```

Compose: redeploy previous image tag; restore DB dump if migration forward-only failed.
