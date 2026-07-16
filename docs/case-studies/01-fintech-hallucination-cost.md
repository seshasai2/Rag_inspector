# Case study: Fintech hallucination cost reduction

## Business

A mid-size digital bank (fictionalized as **Northline Payments**) runs a customer-support RAG assistant over policy PDFs and FAQs. Monthly assisted volume: ~180,000 queries. Average cost of a wrong answer (escalation + goodwill credit) estimated at **$12**.

## Problem

Fluent answers occasionally invented fee waivers and chargeback windows not present in retrieved policy chunks. Sampling found an **8.4%** hallucination rate on policy questions. Leadership lacked a dollarized view to prioritize retrieval fixes vs. LLM prompt changes.

## Architecture

Northline deployed RAGInspector beside the existing LangChain stack:

- Python SDK wrapped retrieve/generate in the support service
- Traces ingested to FastAPI with API keys per environment (staging / prod)
- Celery analysis workers (concurrency 2) on a dedicated node pool
- Dashboard Trust Score + Hallucination Cost wired to pipeline settings (`queries_per_month`, `cost_per_wrong_answer_usd`)

```text
Support API → raginspector SDK → POST /ingest/trace → Postgres
                                      ↓
                               Celery analysis (NLI grounding)
                                      ↓
                               Dashboard cost + query grounding UI
```

## Implementation

1. Instrumented staging for two weeks; tuned chunk metadata (`source`, `effective_date`).
2. Set pipeline cost inputs: 180_000 queries/month, $12 per wrong answer.
3. Triaged top failure types: `hallucination` vs `retrieval_miss`.
4. Used sentence-level grounding to prove model embellishment on fee-waiver questions.
5. Fixed retrieval: boosted policy version filters; added BM25 hybrid after BM25 win rate hit **34%** on fee queries.
6. Added Slack alerts when hallucination rate > 5% over a 1-hour window.

## Results

| Metric | Before (4-week baseline) | After (4-week) |
|--------|--------------------------|----------------|
| Hallucination rate | 8.4% | 3.1% |
| Trust Score | 61.2 | 84.7 |
| Mean grounded_fraction | 0.71 | 0.89 |
| Escalations attributable to bad RAG answers | ~210 / week | ~78 / week |

## ROI

- Implied monthly hallucination cost before: `0.084 × 180_000 × 12 ≈ $181,440`
- After: `0.031 × 180_000 × 12 ≈ $66,960`
- **Gross monthly reduction ≈ $114,480**
- Platform + engineering effort amortized ~$28k first quarter → payback **under 2 weeks** of benefit

## Performance

| Path | p50 | p95 |
|------|-----|-----|
| Ingest `POST /ingest/trace` | 38 ms | 95 ms |
| Analysis job (warm models) | 1.8 s | 4.2 s |
| Dashboard metrics (cached) | 22 ms | 70 ms |

Workers: 3 analysis replicas @ concurrency 1; Redis queue depth stayed < 40 under peak midday load.

## Lessons learned

1. Dollarizing hallucinations beat abstract “faithfulness” charts for executive buy-in.
2. Many “hallucinations” were retrieval misses mislabeled until grounding UI separated sentence support from invention.
3. Keep analysis concurrency low; horizontal replicas drained backlog without OOM.
4. Version metadata on chunks is mandatory for regulated policy corpora.
