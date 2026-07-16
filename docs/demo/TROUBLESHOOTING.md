# Demo troubleshooting

Common demo failures and fixes. Prefer Compose logs over guessing.

## Backend will not become healthy

**Symptoms:** `make bootstrap` waits forever; `/live` times out.

**Checks:**

1. `docker compose ps` — exited containers?
2. `docker compose logs backend --tail=100`
3. `.env` has `SECRET_KEY`; DB URL matches Compose service names.
4. Port `8000` free on the host.

**Fix:** `make down` then `make up`; recreate volumes only if schema corruption (`docker compose down -v` — destroys data).

## Login fails for demo user

1. Run `make seed`.
2. Confirm email/password `demo@example.com` / `DemoPass123!`.
3. If email verification is required in your `.env`, disable for local demo or verify via token logs.
4. Rate limit 429 — wait or set `TESTING`-style disable only in tests, not prod.

## Empty dashboard / no queries

1. Seed may have created traces still `pending` — check workers: `docker compose logs worker`.
2. Confirm worker command includes `-Q analysis,celery`.
3. Call `GET /api/v1/ops/backlog` — pending climbing means workers not draining.
4. Reanalyze: `POST /api/v1/queries/{id}/reanalyze`.

## Ingest returns 401 / 403

1. Header must be `X-API-Key` with the full secret from key creation (not the prefix).
2. Key revoked or wrong user/plan limits — create a new key.
3. Body `pipeline_id` must belong to the key owner.

## Analysis stuck / ML errors

1. Cold start: first task after worker boot is slow — wait ([COLD_START.md](../COLD_START.md)).
2. OOM: lower `--concurrency` to 1; add RAM.
3. Optional HF token issues only affect LLM context-recall path; heuristics still run.

## Frontend cannot reach API

1. Browser console CORS errors — `FRONTEND_URL` / CORS settings in backend.
2. Next.js env pointing at wrong API host.
3. Mixed content if UI is HTTPS and API is HTTP locally — stay on http://localhost for demos.

## `/ops/ready` is 503

Returned body usually marks which dependency failed:

| Check | Action |
|-------|--------|
| database | Postgres up? migrations applied? |
| redis | Redis container healthy? `REDIS_URL` correct? |

Liveness `/live` can still be 200 — that is expected (liveness ≠ readiness).

## Playwright / load tests interfere

Stop Locust/k6 during demos; they can trigger auth rate limits.

## Still stuck

Follow [RUNBOOKS.md](../RUNBOOKS.md) and [INCIDENT_RESPONSE.md](../INCIDENT_RESPONSE.md). Capture `X-Request-ID` from failing responses for log correlation ([LOGGING.md](../LOGGING.md)).
