# Demo dataset

What `make seed` / `backend/scripts/seed_demo.py` (and `app/services/demo_seed.py`) typically create for local demos. Exact row counts may vary by seed revision; treat the shapes below as the expected catalog.

## Accounts

| Field | Value |
|-------|-------|
| Email | `demo@example.com` |
| Password | `DemoPass123!` |
| Plan | Often `pro` or elevated free for demo features |
| Org | Demo organization with owner role |

Create additional users via `/auth/register` for multi-user demos.

## Pipelines

| Name (example) | Purpose |
|----------------|---------|
| Customer Support RAG | Primary dashboard / cost card |
| Docs Assistant | Second pipeline for compare views |

Fields exercised: `queries_per_month` (e.g. 10_000), `cost_per_wrong_answer_usd` (e.g. 5.0).

## Trace categories

Seeded `QueryTrace` rows should cover failure types from `FailureType`:

| Category | What to show |
|----------|--------------|
| Well grounded | High faithfulness + grounded_fraction |
| Hallucination | Answer claims not in chunks |
| Retrieval miss | Low context recall / irrelevant top chunks |
| Coverage gap | Partial sentence support |
| Chunking issue | Fragmented / noisy chunks |

Each analyzed trace includes retrieved chunks with similarity and BM25 scores, and an `AnalysisJob` in `completed` (or pending if workers were down during seed).

## Chunks

- Mix of high and low citation rates for `/chunks` heatmap.
- Flagged chunks illustrate PRD F5 quality rules (`retrieval_count` + low citation).

## API keys

Seed may create a named key for the demo user. If not present, create via `POST /api/v1/keys` after login. Never commit real secrets; rotate local keys freely.

## Re-seeding

```bash
make seed
# or
cd backend && python scripts/seed_demo.py
```

Wipe local SQLite / Compose volumes only when intentionally resetting ([SEED.md](../SEED.md)).

## Synthetic ingest payload

Use the Postman **Ingest Trace** request or:

```json
{
  "pipeline_id": "<uuid>",
  "query": "What is the refund policy?",
  "answer": "Refunds are available within 30 days of purchase with a receipt.",
  "retrieved_chunks": [
    {
      "content": "Customers may request a full refund within 30 days of purchase when they provide a valid receipt.",
      "similarity_score": 0.91,
      "metadata": { "source": "policies.md" }
    }
  ],
  "latency_ms": { "retrieve": 45, "generate": 320 }
}
```
