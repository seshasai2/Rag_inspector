# Optional Terraform modules (provider-agnostic guidance)

This directory is a stub for cloud resource IaC. The application chart remains cloud-agnostic.

Recommended modules (implement in your org's standard tooling):

| Module | Purpose |
|--------|---------|
| network | VPC/VNet, subnets, private endpoints |
| postgres | Managed Postgres + pgvector extension + PITR backups |
| redis | Managed Redis with AUTH + TLS |
| k8s | AKS / EKS / GKE / OpenShift project + node pools |
| secrets | Cloud secret manager + IAM for workload identity |
| dns_tls | DNS + ACM/Let's Encrypt / cert-manager issuers |
| monitoring | Prometheus / Grafana / Cloud monitoring exporters |
| backups | Object storage for DB dumps + lifecycle rules |

Principles:

- No real secrets in `.tf` state committed to git (use remote state + KMS encryption).
- Prefer private networking for Postgres/Redis.
- Wire outputs into Helm `external.*` or External Secrets remote refs.

Application deploy remains: `helm upgrade --install … -f values-production.yaml`
