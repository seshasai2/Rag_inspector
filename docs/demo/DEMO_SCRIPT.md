# Demo script (15–20 minutes)

Live demo outline for RAGInspector: instrument → ingest → analyze → inspect → improve. Assume `make bootstrap` and `make seed` have completed; demo user `demo@example.com` / `DemoPass123!`.

## Minute 0–2 — Setup check

1. Show `docker compose ps` — backend, worker, redis, postgres, frontend healthy.
2. Open http://localhost:8000/live and http://localhost:3000.
3. Optional: `curl -s http://localhost:8000/api/v1/ops/ready | jq`.

## Minute 2–5 — Problem framing

1. State the problem: RAG answers look fluent but may be ungrounded; teams lack sentence-level evidence.
2. Name the product heroes: **Trust Score** and **Hallucination Cost**.
3. Mention open-source stack: FastAPI, Celery, Postgres, Redis, Next.js, sentence-transformers / NLI.

## Minute 5–8 — Dashboard

1. Log in as demo user.
2. Open **Dashboard**: trustworthiness score, hallucination rate, estimated monthly cost.
3. Point at BM25 outperform rate and failure distribution cards.
4. Change pipeline cost assumptions (`queries_per_month`, `cost_per_wrong_answer_usd`) and show cost update.

## Minute 8–12 — Query grounding

1. Navigate to **Queries**; open a seeded hallucinated or partially grounded trace.
2. On query detail, hover answer sentences — supporting chunks highlight (`grounding-attribution`).
3. Call out faithfulness, grounded fraction, context recall, failure type.
4. Show BM25 vs vector scores on chunks.

## Minute 12–15 — Ingest path

1. Show Python SDK snippet (`@trace` / retrieve+generate wrappers) from `sdk/README.md`.
2. Create or reuse an API key under **Settings** / keys API.
3. `POST /api/v1/ingest/trace` via Postman collection or curl; refresh queries list.
4. Mention Celery `analysis` queue and `GET /api/v1/ops/backlog`.

## Minute 15–18 — Ops & trust

1. Chunks heatmap / flagged low-citation chunks.
2. Optionally show `/metrics` timeseries or executive report route.
3. Mention enterprise SSO / audit as roadmap surfaces without blocking the core loop story.

## Minute 18–20 — Close

1. Recap loop: Instrument → Ingest → Analyze → Inspect → Improve.
2. Point recruiters at `docs/ARCHITECTURE.md` and architecture Mermaid set.
3. Q&A: cold start, worker concurrency (1–2), reanalyze after broker outages.

## Demo traps

| Symptom | Fix |
|---------|-----|
| Empty dashboard | `make seed` / wait for worker analysis |
| Login fails | verify seed credentials; email verification gate off in demo |
| Ingest 401 | wrong `X-API-Key` or key revoked |
| Analysis stuck | worker not consuming `analysis` queue |

See [DEMO_WALKTHROUGH.md](DEMO_WALKTHROUGH.md) for UI click-paths and [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for fixes.
