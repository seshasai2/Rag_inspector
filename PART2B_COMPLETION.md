# Part 2B Completion — Frontend, Security, Observability & Operations

**Date:** 2026-07-14  
**Status:** Complete (validated)

## Frontend

### Foundations
- `hooks/usePipelineId.ts` + `usePipelines()` — URL-scoped pipeline filter
- `lib/errors.ts` — `getApiErrorMessage()`
- `lib/cookies.ts` — `sameSite: lax`, `secure` on HTTPS, `path: /`
- Shared `StatusBadge` + `Skeleton`; dark-theme safe status colors
- `PipelineStageGraph` — Embed → Retrieve → Rerank → Generate → Ground → Evaluate

### App shell
- Nav links preserve `?pipeline_id=`
- Mobile drawer navigation
- Accessible labels / `aria-current`

### Pages
- **Query detail** — stage graph, error/retry, dark failure panels, rank latency
- **Dashboard** — ErrorState, chart retry, pipeline-preserving CTAs
- **Metrics / Chunks** — URL-driven pipeline scope + error states
- SSO callback uses secure cookie helpers

## Security / Ops

### Auth
- Failed login + failed MFA recorded in audit log (`auth.login_failed`, `auth.mfa_failed`) with IP/UA (no passwords)

### Health
- `/api/v1/ops/ready` — hard: DB + Redis; soft: migrations + backlog; uptime/version
- Optional `OPS_SHARED_TOKEN` gates `/ops/backlog`, `/metrics`, `/experimental` via `X-Ops-Token`
- `/health` + `/live` remain process liveness; `/ready` remains orchestrator readiness

### Cookies
- Documented: tokens remain JS-readable (Bearer-from-cookie model). HttpOnly migration deferred (needs backend Set-Cookie redesign).

## Validation

| Check | Result |
|-------|--------|
| Backend unit tests | **253 passed** |
| Frontend `tsc --noEmit` | **passed** |
| Frontend Vitest | **19 passed** |
| SDK unittest | **36 passed** |

## Intentionally deferred (not fake-built)
- Full saved-filters / pin / compare-query product UI
- HttpOnly session cookies + BFF
- Every secondary page fully migrated to `usePipelineId` (metrics/chunks/dashboard/shell/query detail done; remaining can follow same pattern)
- GPU/disk/vector-store remote health (not owned by this observability product)
- Real-time websocket push (polling dashboard remains)
