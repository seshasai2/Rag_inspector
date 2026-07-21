# Demo seed dataset

Load a demo user, organization, pipelines, **pre-analyzed** traces, and Phase 10 assets so you can click through the product **without** waiting on Celery/ML.

## Credentials

| Field | Value |
|-------|--------|
| Email | `demo@example.com` |
| Password | `DemoPass123!` |
| API key | `ri-demo_interview_seed_key_000000000001` |
| Org | Acme Support Labs (`acme-support-labs`) |

Email is marked verified; onboarding is completed. Plan is set to **enterprise** so Phase 10 plan gates (monitoring, regression, studio, investigator, reports) are demoable. API key scopes: `ingest:write`, `metrics:read`.

## Run

From the repo (DB must be migrated and reachable via `DATABASE_SYNC_URL`):

```bash
# Local venv
cd backend && python scripts/seed_demo.py

# Refresh traces + Phase 10 assets
cd backend && python scripts/seed_demo.py --force

# Docker
docker compose run --rm backend python scripts/seed_demo.py

# Make
make seed
```

Code: `app/services/demo_seed.py`, CLI `backend/scripts/seed_demo.py`.

## What you get

- User + settings + org membership (owner)
- Pipelines: **Demo RAG Pipeline**, **Docs Assistant**
- Demo API key (printed by CLI; also documented above)
- 4 completed traces: grounded, hallucination, retrieval miss, coverage gap
- Retrieved chunks, sentence grounding, chunk stats (flagged heatmap chunk)
- 2 autofix recommendations
- 2 knowledge gaps, 3 documents (fresh/stale/critical)
- Monitoring config + 2 historical runs
- 2 regression snapshots (baseline + candidate)
- SLA threshold, weekly report subscription, executive report history

Idempotent: second run backfills missing Phase 10 rows; use `--force` to rebuild traces.

## Related

- Quick start: root `README.md`
- Interview mode: [`qa/INTERVIEW_DEMO.md`](qa/INTERVIEW_DEMO.md)
- Dataset detail: [`demo/DEMO_DATASET.md`](demo/DEMO_DATASET.md)
- Worker backlog (optional after seed): [`WORKER.md`](WORKER.md)
