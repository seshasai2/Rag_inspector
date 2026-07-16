# API design guidelines

How RAGInspector shapes HTTP APIs. Interactive schema: `/openapi.json` (non-production).

## Principles

1. **Versioned prefix** — all product APIs under `/api/v1`.
2. **Stable error envelope** — `{ "detail": { "message", "code", "details" } }` for domain errors.
3. **Auth explicit** — JWT Bearer for humans; `X-API-Key` for machines; never mix without documenting.
4. **Async where slow** — ingest returns `202` with `trace_id`; analysis is eventual.
5. **Pagination defaults** — list endpoints return page metadata; enforce max page sizes.
6. **Idempotency awareness** — key create returns secret once; rotate is explicit POST.

## Resource naming

| Pattern | Example |
|---------|---------|
| Noun collections | `/pipelines`, `/queries`, `/keys` |
| Nested actions | `/queries/{id}/reanalyze` |
| Metrics aggregates | `/metrics/dashboard`, `/metrics/timeseries` |
| Ops | `/ops/ready`, `/ops/backlog`, `/ops/metrics` |

Prefer plural nouns. Use POST for non-CRUD verbs (`reanalyze`, `rotate`).

## Status codes

| Code | When |
|------|------|
| 200 | Sync read/update success |
| 201 | Resource created (register, pipeline, key metadata) |
| 202 | Accepted for async work (ingest) |
| 204 | Successful delete with empty body |
| 4xx / 5xx | See [API.md](../API.md) |

## Request / response

- JSON only for `/api/v1` (except Prometheus text on `/ops/metrics`).
- Use Pydantic schemas in `app/schemas/schemas.py` as the contract.
- Echo `X-Request-ID` / `X-Correlation-ID` / `X-Trace-ID`.
- Avoid breaking field renames; add fields additively.

## Rate limiting

Document limits on abusive surfaces (auth, ingest). Clients should retry 429 with backoff.

## Compatibility

- Deprecate via docs + OpenAPI description before removal.
- Production disables `/docs` and `/redoc`; ship Postman/Insomnia exports for partners.

Related: [API.md](../API.md), [CODING_STANDARDS.md](CODING_STANDARDS.md).
