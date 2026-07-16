# Case study: Healthcare retrieval quality

## Business

**Riverbend Health** (composite) operates a clinician-facing RAG assistant over clinical guidelines and formulary documents. Accuracy requirements are high; false confidence is unacceptable.

## Problem

Vector-only retrieval frequently ranked outdated guideline snippets above current ones. Context recall on a 500-question gold set averaged **0.52**, with nurses reporting “right document, wrong section” failures. No shared tooling linked answers back to cited passages.

## Architecture

- On-prem Kubernetes install of RAGInspector (air-gapped HF models)
- Ingest from internal FastAPI proxy; no public internet for PHI traces
- Postgres + Redis in the same cluster; SSO via existing Okta OIDC
- Grounding with local NLI; LLM context-recall path disabled (`HF_API_TOKEN` unset)

## Implementation

1. Imported gold set as regression suite (`/regression`) with expected chunk ids.
2. Enabled document freshness worker to flag guides older than policy SLA.
3. Used BM25 comparison metrics: lexical win rate **41%** on drug-name queries → hybrid retrieval.
4. Chunk quality job flagged sections with citation_rate < 0.20 at high retrieval count — re-chunked tables and dosage lists.
5. Query detail grounding became mandatory review for any answer marked `retrieval_irrelevant`.

## Results

| Metric | Baseline | After 6 weeks |
|--------|----------|---------------|
| Context recall (gold set) | 0.52 | 0.78 |
| Retrieval_miss failure share | 39% | 17% |
| Mean context_precision_score | 0.61 | 0.83 |
| Guidelines flagged stale / week | — | 12–18 actionable |

Clinician satisfaction (internal pulse, n=46): “I can verify the sentence quickly” rose from 2.4 → 4.1 / 5.

## ROI

- Avoided estimated **120** duplicate literature consults / month at ~45 minutes each → ~90 hours clinician time (~$18k / month loaded cost).
- Reduced time-to-validate answers in chart review from ~4.5 min to ~1.2 min median.

## Performance

Air-gapped cold start for NLI+embeddings: **47 s** per analysis worker; warm analysis p95 **5.1 s**. API readiness (`/ops/ready`) p95 **18 ms** inside cluster.

## Lessons learned

1. Healthcare value was retrieval diagnostics, not generic chat analytics.
2. Disabling cloud LLM judges simplified compliance while heuristics + NLI remained useful.
3. Freshness signals prevented “accurate yesterday” answers on rotated formularies.
4. Gold-set regression caught silent embedding-model upgrades that tanked recall.
