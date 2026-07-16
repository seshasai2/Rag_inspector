# Part 3A.2 — Kubernetes, IaC, Secrets, Production Ops

Status: **Complete**

## Delivered

| Area | Location |
|------|----------|
| Helm chart | `infrastructure/helm/raginspector` (+ values-development/staging/production) |
| K8s references | `infrastructure/kubernetes/` |
| Terraform guidance | `infrastructure/terraform/README.md` |
| External Secrets example | `infrastructure/kubernetes/examples/externalsecret.yaml` |
| Health probes | Startup/Live `/live`; Ready `/api/v1/ops/ready` (DB+Redis) |
| HPA / PDB / NetworkPolicy | Chart templates |
| Optional KEDA | `templates/keda-scaledobject.yaml` |
| ServiceMonitor / PrometheusRule | Optional via values |
| Migration + validate Jobs | Helm hooks — release fails if validate fails |
| SBOM | `scripts/generate_sbom.py` + CI artifact |
| Helm validate | `scripts/validate_helm_chart.py` + CI job |
| Release validate | `scripts/validate_release.py` |
| Docs | KUBERNETES, HELM, SECRETS, AUTOSCALING, BACKUP, RUNBOOKS, SRE_CHECKLIST, SUPPLY_CHAIN; DR/DEPLOYMENT/LOGGING updated |
| Compose fix | `OPS_SHARED_TOKEN` wired into `docker-compose.prod.yml` |

## CI additions

- `helm` job: lint + template render upload
- `sbom` job: CycloneDX inventories
- Docker image Trivy (CRITICAL) after Buildx load
- Release gate `needs` includes helm + sbom

## Validate locally

```bash
python scripts/validate_helm_chart.py   # structure; helm lint/template if helm installed
python scripts/generate_sbom.py
make helm-validate
```

## Production install (repeatable)

1. Create Secret (`docs/SECRETS.md`)
2. `helm upgrade --install … -f values-production.yaml`
3. `python scripts/validate_release.py`

No undocumented production-only steps beyond org-specific registry/DNS/secret-manager wiring documented as external prerequisites.

## SRE checklist

See `docs/SRE_CHECKLIST.md` — all categories Met except Performance (Partial: baselines set, soak pending).

Do not proceed to Part 3B until this completion report is accepted.
