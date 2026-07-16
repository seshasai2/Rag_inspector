# Case study: SaaS pre-deploy regression

## Business

**Stackline Cloud** ships a B2B knowledge assistant weekly. Broken retrieval after embedding-model bumps caused two customer-visible regressions in one quarter.

## Problem

CI checked unit tests and API contracts but **not** RAG quality. A sentence-transformer upgrade dropped faithfulness on product-pricing questions by **11 points** and was noticed only after support tickets.

## Architecture

- RAGInspector staging project per git environment
- CI job: ingest recorded fixtures → wait for analysis → assert thresholds via SDK + metrics API
- Regression feature module compared current run vs baseline trust / hallucination / BM25 rates
- Gate: block deploy if Trust Score delta < −5 or hallucination rate > 6%

## Implementation

1. Captured 200 production-like traces (anonymized) as fixtures.
2. Nightly and pre-deploy pipelines: `POST /ingest/trace` batch, poll until `AnalysisJob.completed`.
3. Asserted:

   - `trustworthiness_score >= 80`
   - `hallucination_rate <= 0.05`
   - `context_recall_score` mean >= 0.65

4. Stored run history for `/regression` UI so PMs could see which queries flipped failure type.
5. On failure, linked CI to query ids for grounding review.

## Results

| Metric | Before gates | After 3 months |
|--------|--------------|----------------|
| Customer-visible RAG regressions / quarter | 2 | 0 |
| Deploy rollbacks for answer quality | 3 | 0 |
| Mean time to detect quality drop | ~5 days | ~18 minutes (CI) |
| False-positive gate failures | — | 4 (tuned thresholds) |

## ROI

- Prevented estimated **$64k** in churn credit + engineer firefight from one avoided pricing hallucination incident (finance postmortem).
- CI cost: ~12 min extra on runners + staging workers; < **$400** / month cloud.

## Performance

Full fixture analysis wall time: **6.5 minutes** for 200 traces on 4 warm workers. Ingest p95 **110 ms** under CI parallelism 10.

## Lessons learned

1. Treat RAG metrics as release artifacts, not dashboards alone.
2. Thresholds need weeks of baseline; start warn-only then enforce.
3. Fixtures must include known hallucination and retrieval-miss cases or gates stay green while UX burns.
4. Reanalyze endpoint is essential when workers lag in shared staging clusters.
