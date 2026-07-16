# Infrastructure As Code

Moved to **`infrastructure/`** (Helm chart, Kubernetes references, Terraform guidance).

This `infra/` tree retains shared observability scrape configs used by Docker Compose overlays:

- `infra/observability/prometheus.yml`
- `infra/observability/grafana/provisioning/`

See `infrastructure/README.md` and `docs/KUBERNETES.md`.
