# Changelog

All notable changes to RAGInspector are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Prometheus scrape: `/api/v1/ops/metrics` now returns `PlainTextResponse` (was JSON-encoded string → `up=0`)
- Critical coverage gate regression: `ingest_service` unit tests restore backend critical coverage to ≥95% (was 91.8%)

### Documentation
- Canonical engineering guide: `PROJECT_GUIDE.md`
- Consolidated performance baselines: `docs/engineering/PERFORMANCE.md`
- Removed superseded audit/completion/performance report sprawl (see `docs/REMOVED.md`)

### Security
- Access JWT Redis denylist on logout (optional `access_token` + `revoke_all_sessions`)
- Org-scoped pipeline ACL: accepted members can read org-tagged pipelines; mutations stay owner-only
- Denylist fail-open Prometheus counter + Grafana alert (`JwtDenylistFailOpen`)

### Observability
- Real HTTP RED Prometheus metrics (`raginspector_http_requests_total`, latency histogram)
- Grafana alert rules for 5xx rate and p99 latency
- Prometheus recording rules for multi-replica RED aggregation
- Optional OpenTelemetry bootstrap when `OTEL_EXPORTER_OTLP_ENDPOINT` is set (`requirements-otel.txt`)

### UX
- Dark/light theme toggle (persisted) with hydration-safe bootstrap script
- Demo grounding screenshot PNG (`docs/screenshots/grounding-attribution.png`)

### Performance
- Batch ChunkStat citation updates in analysis grounding stage (eliminates per-chunk N+1)

### Testing / CI
- Explicit `--cov-fail-under=95` backend gate; frontend Vitest coverage gate on critical lib/components
- Integration suite wired into CI; denylist/metrics/org ACL/OTel/theme tests

### DX
- Windows `scripts/bootstrap.ps1` twin of `make bootstrap`
- Top-level `docs/TROUBLESHOOTING.md` index

### Infrastructure
- Enterprise CI pipeline (lint, types, tests, Docker builds, security scans, artifacts)
- Multi-stage Docker images with non-root runtime users
- SDK `pyproject.toml` packaging (PyPI-ready)
- Optional observability Compose overlay (Prometheus + Grafana)
- `make bootstrap` one-command local bring-up
- Kubernetes-ready Helm chart (`infrastructure/helm/raginspector`) with NetworkPolicies, HPA, PDB, probes, migration/validate hooks
- Secrets, backup, DR, runbooks, SRE checklist, supply-chain / SBOM tooling

## [1.0.0] - 2026-07-14

### Features
- RAG observability platform: ingest, analysis workers, grounding, RAGAS metrics, dashboard
- Python SDK with retrieval/generation/embedding decorators and framework adapters
- Enterprise surfaces: MFA, RBAC, audit logs, monitoring, regression, reports

### Security
- Production settings fail-closed validation
- Optional ops token for backlog/metrics endpoints
- Dependency and secret scanning in CI
