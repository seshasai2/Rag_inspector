# Case study: Enterprise SSO and observability

## Business

**Globex Industrial** (composite Fortune 500 manufacturer) required SSO, audit trails, and SRE-grade telemetry before enterprise procurement would approve a RAG debugger for three business units.

## Problem

Shadow IT teams evaluated the open-source stack but security rejected local username/password as the only auth path. Ops needed backlog SLOs for analysis latency and evidence of structured audit logs for access reviews.

## Architecture

- Enterprise plan deployment on customer EKS
- OIDC via Azure AD (`/api/v1/identity/sso/...`) with org `sso_required=true`
- Optional MFA enrollment for break-glass local admins
- SCIM stubs evaluated for joiner/mover/leaver (pilot)
- Prometheus scrape of `/api/v1/ops/metrics`; Grafana dashboards for queue depth and analysis backlog
- Audit log API for admin actions (`/api/v1/audit-logs`)

## Implementation

1. Hardened production compose/Helm: Trusted hosts, CORS lock, secrets from AWS SM ([SECRETS.md](../SECRETS.md)).
2. Configured SSO connections; mapped groups to `admin` / `engineer` / `viewer`.
3. Turned on MFA requirement for org owners.
4. SRE alerts:

   - `raginspector_analysis_backlog > 200` for 10m
   - `/ops/ready` != ready for 2m
   - p95 analysis job duration > 15s

5. Quarterly access review exported from audit logs (API key create/rotate, SSO connect, member role changes).

## Results

| Metric | Outcome |
|--------|---------|
| Security questionnaire | Passed after SSO + audit evidence pack |
| Time to provision new BU | 2 days → **3 hours** (SSO group map) |
| Mean analysis backlog under peak | 240 → **35** after HPA on workers |
| Unreviewed admin actions / quarter | Unknown → **0** (process + audit) |

## ROI

- Unlocked enterprise contract covering 3 BUs (~**$186k** ARR) that was blocked on IdP requirements.
- Reduced duplicate home-grown trace logging projects (~2 FTE months saved).

## Performance

| Signal | Target | Achieved |
|--------|--------|----------|
| API `/live` p99 @ 500 VU | < 200 ms | 140 ms (in-cluster) |
| `/ops/ready` p99 | < 300 ms | 220 ms |
| SSO login interactive | < 3 s redirect round-trip | ~1.8 s median |
| Analysis p95 warm | < 6 s | 4.7 s |

Load validated with repo k6 scripts against staging ingress.

## Lessons learned

1. SSO and audit are procurement features as much as product features.
2. Split analysis vs default Celery queues so webhook/SSO callbacks never starve ML workers.
3. Readiness distinct from liveness prevented Kubernetes from killing pods during Redis blips while still alerting.
4. Document rate limits and request IDs early — enterprise security reviewers will ask.

Related open-source references: FastAPI Security, Keycloak/Azure AD OIDC docs, Prometheus client patterns, Grafana dashboards under `infra/`.
