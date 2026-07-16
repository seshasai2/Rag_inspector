# Raw Kubernetes reference manifests
#
# Primary deploy path is Helm: `infrastructure/helm/raginspector`.
# Render raw YAML for review or GitOps without Helm install:
#
#   helm template raginspector ./infrastructure/helm/raginspector \
#     -f infrastructure/helm/raginspector/values-production.yaml \
#     > infrastructure/kubernetes/rendered-production.yaml
#
# Validate:
#   kubectl apply --dry-run=client -f infrastructure/kubernetes/rendered-production.yaml
#   python scripts/validate_helm_chart.py
#
# examples/ — patterns for External Secrets (future), not installed by default.

See docs/KUBERNETES.md
