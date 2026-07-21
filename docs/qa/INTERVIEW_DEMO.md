# Interview Demo Mode (Phase 11)

Goal: demonstrable in **10–15 minutes** without waiting on model downloads or long Celery jobs.

## Pre-flight (once per machine)

```bash
cp .env.example .env   # set SECRET_KEY
docker compose up -d --build
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python scripts/seed_demo.py --force
```

Windows port conflicts: add `docker-compose.verify-ports.yml` and/or see `docs/WINDOWS.md`.  
Low RAM: add `docker-compose.interview.yml`.

## Demo accounts & assets (seeded)

| Asset | Value |
|-------|--------|
| User | `demo@example.com` / `DemoPass123!` |
| Org | Acme Support Labs |
| API key | `ri-demo_interview_seed_key_000000000001` |
| Pipelines | Demo RAG Pipeline, Docs Assistant |
| Traces | 4 completed (grounded, hallucination, retrieval miss, coverage gap) |
| Gaps | 2 open knowledge gaps |
| Documents | 3 (fresh / stale / critical) |
| Monitoring | Config + 2 historical runs |
| Regression | baseline-v1.0 + pre-deploy-candidate |
| Reports | Executive history entry |
| Autofix | 2 open recommendations |

Models: **not required** for seeded UI. Optional live ingest uses `all-MiniLM-L6-v2` + `cross-encoder/nli-deberta-v3-small` (free HF).

## 12-minute script

| Min | Action |
|-----|--------|
| 0–1 | `/live` + `/ops/ready` + UI open |
| 1–3 | Login → Dashboard trust + hallucination cost |
| 3–6 | Queries → hallucination grounding hover |
| 6–8 | Chunks flagged + Knowledge gaps |
| 8–10 | Documents freshness + Regression compare |
| 10–12 | Optional: curl ingest with demo API key **or** Executive report; close |

Full narrative: [DEMO_SCRIPT.md](../demo/DEMO_SCRIPT.md).

## Do not demo live (unless prepared)

- Razorpay checkout (needs keys)
- Google SSO (needs OAuth client)
- Cold worker first analysis on tiny RAM hosts (prefer seed)

## Screenshots

Capture after seed if refreshing portfolio: `docs/screenshots/` (see README there).
