# Demo dataset

What `make seed` / `backend/scripts/seed_demo.py` creates. Source of truth: `app/services/demo_seed.py`.

## Accounts

| Field | Value |
|-------|-------|
| Email | `demo@example.com` |
| Password | `DemoPass123!` |
| Plan | `enterprise` (unlocks Phase 10 demo surfaces) |
| Org | Acme Support Labs (`acme-support-labs`) |
| API key | `ri-demo_interview_seed_key_000000000001` |

## Pipelines

| Name | Purpose |
|------|---------|
| Demo RAG Pipeline | Primary dashboard / cost / Phase 10 assets |
| Docs Assistant | Second pipeline for compare views |

Fields: `queries_per_month`, `cost_per_wrong_answer_usd`.

## Trace categories

| Category | Failure type |
|----------|--------------|
| Well grounded | `none` |
| Hallucination | `hallucination` |
| Retrieval miss | `retrieval_miss` |
| Coverage gap | `coverage_gap` |

Each analyzed trace includes retrieved chunks (similarity + BM25), grounding sentences, and a completed `AnalysisJob`.

## Phase 10 assets

| Asset | Count / notes |
|-------|----------------|
| Knowledge gaps | 2 open (API keys, enterprise SLA) |
| Documents | 3 (fresh / stale / critical) |
| Monitoring | enabled config + 2 runs |
| Regression snapshots | `baseline-v1.0`, `pre-deploy-candidate` |
| Autofix | 2 open recommendations |
| Reports | 1 executive history JSON |
| SLA | trust_score_min 75 |

## Chunks

- Mix of high and low citation rates for `/chunks`.
- Flagged: `doc-onboarding-01` (high retrieval, low citation).

## Synthetic ingest payload

Use `docs/qa/assets/payloads/ingest_trace.json` or:

```json
{
  "pipeline_name": "Demo RAG Pipeline",
  "query_text": "What is the refund policy?",
  "answer_text": "Refunds are available within 14 days of purchase.",
  "retrieved_chunks": [
    {
      "chunk_id": "doc-billing-01",
      "chunk_text": "Annual subscriptions may be refunded in full within 14 days.",
      "similarity_score": 0.91
    }
  ],
  "embed_latency_ms": 12,
  "retrieve_latency_ms": 45,
  "generate_latency_ms": 320
}
```

Header: `X-API-Key: ri-demo_interview_seed_key_000000000001`

## Re-seeding

```bash
make seed
# or
cd backend && python scripts/seed_demo.py --force
```

See [SEED.md](../SEED.md) and [qa/INTERVIEW_DEMO.md](../qa/INTERVIEW_DEMO.md).
