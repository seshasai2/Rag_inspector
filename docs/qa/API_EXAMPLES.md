# API Examples (Phase 6)

Base URL: `http://localhost:8000` (or `https://raginspector-api.onrender.com`).

Variables after seed:
- `EMAIL=demo@example.com`
- `PASSWORD=DemoPass123!`
- `API_KEY=ri-demo_interview_seed_key_000000000001`
- `PIPELINE_ID` — from login → list pipelines (stable seed UUID for Demo RAG Pipeline)

Also import: [postman_collection.json](../api/postman_collection.json), [insomnia_collection.json](../api/insomnia_collection.json), [http/raginspector.http](../api/http/raginspector.http).

---

## Health

```bash
curl -sS "$BASE/live"
# 200 {"status":"healthy","version":"..."}

curl -sS "$BASE/api/v1/ops/ready"
# 200 when DB+Redis ok; 503 with failed checks when not
```

## Auth

```bash
# Login — expected 200
curl -sS -X POST "$BASE/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"DemoPass123!"}'
# → access_token, refresh_token

# Invalid login — expected 401
curl -sS -o /dev/null -w "%{http_code}\n" -X POST "$BASE/api/v1/auth/login" \
  -H 'Content-Type: application/json' \
  -d '{"email":"demo@example.com","password":"wrong"}'

# Me
curl -sS "$BASE/api/v1/auth/me" -H "Authorization: Bearer $TOKEN"

# Refresh
curl -sS -X POST "$BASE/api/v1/auth/refresh" \
  -H 'Content-Type: application/json' \
  -d "{\"refresh_token\":\"$REFRESH\"}"

# Missing auth — expected 401
curl -sS -o /dev/null -w "%{http_code}\n" "$BASE/api/v1/auth/me"
```

## Pipelines & keys

```bash
curl -sS "$BASE/api/v1/pipelines" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/keys" -H "Authorization: Bearer $TOKEN"
```

## Ingest (API key)

```bash
curl -sS -X POST "$BASE/api/v1/ingest/trace" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $API_KEY" \
  -d @docs/qa/assets/payloads/ingest_trace.json
# 200/201 with trace_id; 401 without key; 422 invalid body; 429 on plan limit
```

Payload shape (required fields): `pipeline_name`, `query_text`, `retrieved_chunks[].chunk_id` + `chunk_text`. Optional: `answer_text`, latency fields.

Missing key:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" -X POST "$BASE/api/v1/ingest/trace" \
  -H 'Content-Type: application/json' \
  -d '{}'
# 401 or 422
```

## Queries & metrics

```bash
curl -sS "$BASE/api/v1/queries?page=1&per_page=20" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/queries/$TRACE_ID" -H "Authorization: Bearer $TOKEN"
curl -sS -X POST "$BASE/api/v1/queries/$TRACE_ID/reanalyze" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/metrics/dashboard" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/chunks/summary" -H "Authorization: Bearer $TOKEN"
```

## Phase 10

```bash
curl -sS "$BASE/api/v1/knowledge/gaps" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/autofix/recommendations" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/documents" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/documents/freshness" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/monitoring/config/$PIPELINE_ID" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/monitoring/history/$PIPELINE_ID" -H "Authorization: Bearer $TOKEN"
curl -sS -X POST "$BASE/api/v1/monitoring/run-now/$PIPELINE_ID" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/regression/snapshots/$PIPELINE_ID" -H "Authorization: Bearer $TOKEN"
curl -sS -X POST "$BASE/api/v1/regression/compare" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d @docs/qa/assets/payloads/regression_compare.json
curl -sS -X POST "$BASE/api/v1/studio/prompt/analyze" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d @docs/qa/assets/payloads/studio_prompt.json
curl -sS -X POST "$BASE/api/v1/investigator/ask" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"question":"What is our current trust score?"}'
curl -sS "$BASE/api/v1/reports/executive" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/reports/history" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/organizations/current" -H "Authorization: Bearer $TOKEN"
curl -sS "$BASE/api/v1/billing/usage" -H "Authorization: Bearer $TOKEN"
```

## Edge cases (expected)

| Case | Request | Expected |
|------|---------|----------|
| Expired/garbage JWT | `Authorization: Bearer x` | 401 |
| Wrong API key | `X-API-Key: ri-nope` | 401 |
| Empty ingest chunks | payload with `retrieved_chunks: []` | 422 or accepted with low quality |
| Unknown pipeline_id | random UUID | 404 |
| Permission other user resource | foreign id | 403/404 |

## Error shape

Typically FastAPI: `{"detail": "..."}` or validation `{"detail":[...]}`.
