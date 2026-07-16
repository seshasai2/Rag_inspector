# Demo seed dataset (Phase 7.3)

Load a demo user, pipeline, and **pre-analyzed** sample traces so you can click through Dashboard / Queries / Chunks **without** running a real RAG app or waiting on Celery/ML.

## Credentials

| Field | Value |
|-------|--------|
| Email | `demo@example.com` |
| Password | `DemoPass123!` |

Email is marked verified; onboarding is completed.

## Run

From the repo (DB must be migrated and reachable via `DATABASE_SYNC_URL`):

```bash
# Local venv
cd backend && python scripts/seed_demo.py

# Refresh traces
cd backend && python scripts/seed_demo.py --force

# Docker
docker compose run --rm backend python scripts/seed_demo.py

# Make
make seed
```

Code: `app/services/demo_seed.py`, CLI `backend/scripts/seed_demo.py`.

## What you get

- User + settings + **Demo RAG Pipeline**
- 4 completed traces: grounded, hallucination, retrieval miss, coverage gap
- Retrieved chunks, sentence grounding, chunk stats (one flagged for heatmap), one fix recommendation

Idempotent: second run prints credentials and skips unless `--force`.

## Related

- Quick start: root `README.md`
- Worker backlog (optional after seed): [`WORKER.md`](WORKER.md)
