# RAGInspector API

REST API for authentication, pipeline management, SDK ingest, query inspection, metrics, and operations. Interactive docs are served by FastAPI (disabled in production).

## Interactive documentation

| Tool | URL (local default) | Notes |
|------|---------------------|-------|
| OpenAPI JSON | http://localhost:8000/openapi.json | Machine-readable schema |
| Swagger UI | http://localhost:8000/docs | Try-it-out (non-production) |
| ReDoc | http://localhost:8000/redoc | Readable reference (non-production) |

In `ENVIRONMENT=production`, `/docs` and `/redoc` are disabled; use this document plus exported collections:

- [api/postman_collection.json](api/postman_collection.json)
- [api/insomnia_collection.json](api/insomnia_collection.json)

Base path for versioned routes: **`/api/v1`**. Liveness lives at the root: `/live`, `/health`.

## Authentication

### JWT (dashboard)

1. `POST /api/v1/auth/register` — create account (rate limit `10/minute`).
2. Verify email if your deployment gates unverified users.
3. `POST /api/v1/auth/login` — returns `access_token`, `refresh_token` (or MFA challenge).
4. Send `Authorization: Bearer <access_token>` on protected routes.
5. `POST /api/v1/auth/refresh` before access expiry; `POST /api/v1/auth/logout` to revoke.

### API key (SDK ingest)

1. Authenticate with JWT and `POST /api/v1/keys` to create a key (secret shown once).
2. Send `X-API-Key: <secret>` on `POST /api/v1/ingest/trace`.
3. Rotate with `POST /api/v1/keys/{id}/rotate`; delete with `DELETE /api/v1/keys/{id}`.

### Roles and plans

Org roles (`owner`, `admin`, `engineer`, `analyst`, `developer`, `viewer`) gate admin, audit, and identity endpoints. Subscription plans (`free`, `starter`, `pro`, `enterprise`) gate usage and enterprise features via plan checks in `app/core/plan_gate.py`.

## Rate limits

Implemented with SlowAPI (`app/core/rate_limit.py`). Limits are per client IP and disabled when `TESTING=1`.

| Surface | Limit |
|---------|-------|
| Register | 10 / minute |
| Login | 20 / minute |
| Refresh | 30 / minute |
| Password reset / resend verify | 5 / minute |
| Ingest trace | 120 / minute |
| Ingest batch (if enabled) | 30 / minute |

Exceeding a limit returns HTTP **429** with SlowAPI’s default error body. Respect `Retry-After` when present.

## Error model

Domain errors (`BaseRAGInspectorError`) serialize as:

```json
{
  "detail": {
    "message": "Human-readable explanation",
    "code": "validation_error",
    "details": {}
  }
}
```

| HTTP | Typical codes | Meaning |
|------|---------------|---------|
| 400 | `validation_error` | Bad input that is not a schema failure |
| 401 | — | Missing/invalid JWT or API key |
| 403 | — | Authenticated but forbidden (role / plan / email gate) |
| 404 | — | Unknown resource id |
| 409 | — | Conflict (duplicate email, etc.) |
| 422 | `validation_error`, pydantic | Request body / query validation |
| 429 | rate limit | Too many requests |
| 502 / 504 | `provider_error`, `network_error`, `timeout_error` | Upstream LLM / network |
| 503 | `configuration_error`, `database_error`, `worker_error` | Dependency unavailable |

All responses include `X-Request-ID`, `X-Correlation-ID`, and `X-Trace-ID` for log correlation ([LOGGING.md](LOGGING.md)).

## Response schemas overview

| Area | Key schemas | Endpoints |
|------|-------------|-----------|
| Auth | `UserOut`, `LoginResponse`, `TokenResponse` | `/auth/*` |
| Keys | `APIKeyOut`, `APIKeyCreated` | `/keys` |
| Pipelines | `PipelineOut`, stats/compare JSON | `/pipelines` |
| Ingest | `TraceIngestResponse` (`202` + `trace_id`) | `/ingest/trace` |
| Queries | `PaginatedTraces`, `QueryTraceDetail` | `/queries` |
| Chunks | `PaginatedChunks`, summary | `/chunks` |
| Metrics | dashboard, timeseries, BM25, failures, latency | `/metrics/*` |
| Ops | readiness JSON, backlog, Prometheus text | `/ops/*` |
| Settings | `UserSettingsOut` | `/settings` |

Pagination defaults and caps: `per_page` / `limit` ≤ 100 (admin/audit ≤ 200) — `app/core/pagination.py`.

## Core endpoints quick reference

| Method | Path | Auth |
|--------|------|------|
| GET | `/live`, `/health` | none |
| GET | `/api/v1/ops/ready` | none (DB + Redis checks) |
| POST | `/api/v1/auth/register`, `/login`, `/refresh`, `/logout` | public / refresh |
| GET | `/api/v1/auth/me` | JWT |
| CRUD | `/api/v1/pipelines` | JWT |
| CRUD | `/api/v1/keys` | JWT |
| POST | `/api/v1/ingest/trace` | API key |
| GET | `/api/v1/queries`, `/queries/{id}` | JWT |
| GET | `/api/v1/metrics/dashboard` | JWT |

## Client collections

Import Postman or Insomnia collections from `docs/api/` and set collection variables:

| Variable | Example |
|----------|---------|
| `baseUrl` | `http://localhost:8000` |
| `accessToken` | from login |
| `apiKey` | from key create |
| `pipelineId` | from pipeline create |
| `traceId` | from ingest / query list |

## Related

- Architecture: [architecture/README.md](architecture/README.md)
- API design rules: [engineering/API_DESIGN.md](engineering/API_DESIGN.md)
- Load tests: [../loadtests/README.md](../loadtests/README.md)
