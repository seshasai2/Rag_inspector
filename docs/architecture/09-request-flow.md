# Typical authenticated request flow

End-to-end path for a dashboard JWT request (for example `GET /api/v1/metrics/dashboard`) and how middleware, auth, caching, and logging wrap the handler.

```mermaid
sequenceDiagram
    autonumber
    participant FE as Next.js
    participant MW as Middleware<br/>request_id · CORS · security headers · SlowAPI
    participant DEP as deps.get_current_user
    participant EP as metrics.dashboard
    participant CACHE as Redis dashboard_cache
    participant SVC as dashboard_metrics
    participant DB as PostgreSQL

    FE->>MW: HTTPS GET + Bearer JWT<br/>X-Request-ID optional
    MW->>MW: bind request_id / correlation_id / trace_id
    MW->>DEP: inject credentials
    DEP->>DB: load user (active, email gate)
    DEP-->>EP: current_user
    EP->>CACHE: get cached dashboard payload
    alt cache hit
        CACHE-->>EP: JSON blob
    else cache miss
        EP->>SVC: compute trust, hallucination cost, BM25 rates
        SVC->>DB: aggregate recent traces / pipelines
        SVC-->>EP: metrics dict
        EP->>CACHE: set TTL
    end
    EP-->>MW: 200 JSON
    MW-->>FE: + X-Request-ID · X-Correlation-ID · X-Trace-ID
```

Notes:

- Failed dependency auth returns `401` / `403` before the endpoint runs.
- Domain errors (`BaseRAGInspectorError`) map to stable `{ detail: { message, code, details } }` JSON.
- Ingest requests skip JWT and use API-key resolution instead; they still receive request ID headers.

See also: [03-dashboard-sequence.md](03-dashboard-sequence.md), [DASHBOARD_CACHE.md](../DASHBOARD_CACHE.md).
