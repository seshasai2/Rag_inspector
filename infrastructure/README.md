# Infrastructure As Code — RAGInspector
#
# Layout:
#   kubernetes/     Raw / reference Kubernetes manifests (generated examples + README)
#   helm/       Production Helm chart (primary deploy path)
#   terraform/  Optional cloud resource stubs (provider-agnostic guidance)
#
# Prefer Helm for installs. Raw manifests illustrate shapes without chart templating.
# Never commit real secrets — use Sealed Secrets / External Secrets / cloud secret managers.

See:
- docs/KUBERNETES.md
- docs/HELM.md
- docs/SECRETS.md
- docs/RUNBOOKS.md
- docs/SRE_CHECKLIST.md
- docs/SUPPLY_CHAIN.md
- docs/AUTOSCALING.md
- docs/BACKUP.md
