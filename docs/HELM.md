# Helm chart

Chart path: `infrastructure/helm/raginspector`

## Values files

| File | Intent |
|------|--------|
| `values.yaml` | Defaults |
| `values-development.yaml` | In-cluster Postgres/Redis, small replicas |
| `values-staging.yaml` | External DB/Redis, HA starters |
| `values-production.yaml` | Managed data plane, stricter PDB/HPA/TLS |

## Configurable knobs

Image tags, replicas, resources, ingress/TLS, env (`config.*`), secrets, nodeSelector/affinity/tolerations, HPA, persistence (model cache), ServiceMonitor, PrometheusRules, KEDA ScaledObject, NetworkPolicies.

## Commands

```bash
helm lint ./infrastructure/helm/raginspector -f ./infrastructure/helm/raginspector/values-production.yaml
helm template raginspector ./infrastructure/helm/raginspector \
  -f ./infrastructure/helm/raginspector/values-production.yaml > /tmp/ri.yaml
python scripts/validate_helm_chart.py

helm upgrade --install raginspector ./infrastructure/helm/raginspector \
  -f ./infrastructure/helm/raginspector/values-staging.yaml \
  -n raginspector-staging --create-namespace
```

## Hooks

| Hook | When | Purpose |
|------|------|---------|
| Migration Job | `post-install`, `pre-upgrade` | `alembic upgrade head` |
| Validate Job | `post-install`, `post-upgrade` | curl `/live`, `/ops/ready`, frontend `/` |

Release **fails** if validate Job fails (critical path).

## Rolling updates

Backend/frontend: `maxUnavailable: 0`, `maxSurge: 1` (zero-downtime ready).
Beat: `Recreate` (singleton scheduler).
Worker: graceful `preStop` Celery shutdown + `terminationGracePeriodSeconds: 120`.

## Canary / blue-green

Chart is rolling-update ready. For canary: deploy a second release name (`raginspector-canary`) with traffic splitting at the Ingress/mesh layer; promote by pointing Ingress service to stable. Not packaged as a second chart to avoid cloud-specific mesh assumptions.
