# SRE checklist (Part 3A.2)

Assessment against enterprise operational standards. Ratings: **Met** / **Partial** / **Gap**.

| Category | Rating | Evidence / notes |
|----------|--------|------------------|
| Availability | Met | Multi-replica API/UI, PDBs, rolling updates `maxUnavailable:0`, readiness on DB+Redis |
| Reliability | Met | Fail-fast prod config; migration + validate Helm hooks; structured health |
| Scalability | Met | HPA CPU/memory; optional KEDA queue; documented assumptions (`AUTOSCALING.md`) |
| Recoverability | Met | Backup + DR docs; managed PITR recommended; Compose dump sidecar |
| Maintainability | Met | Helm values per env; runbooks; IaC under `infrastructure/` |
| Security | Met | Non-root, drop caps, RO rootfs, NetworkPolicies, secrets externalized, TLS ingress |
| Performance | Partial | Resource baselines set; need production load soak to refine limits |
| Observability | Met | `/live`, `/ops/ready`, `/ops/metrics`, ServiceMonitor/Rules optional, log guidance |
| Operational simplicity | Met | `helm upgrade` + `validate_release.py`; Compose `make bootstrap` for lab |

## Open follow-ups (non-blocking)

- Promote image digests in a private registry (org-specific).
- Wire real Grafana dashboards JSON for prod monitoring stack.
- Confirm RPO/RTO per customer contract before enterprise SLA sign-off.

## Sign-off checklist

- [ ] Helm lint/template green in CI
- [ ] Secrets created via manager (not git)
- [ ] Ingress TLS verified (HSTS path)
- [ ] NetworkPolicies reviewed for ingress controller namespace names
- [ ] Backup restore drill completed in last 30 days
- [ ] `scripts/validate_release.py` passed against staging
