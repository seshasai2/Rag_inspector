# Case study: Legal-tech vector database evaluation

## Business background

**Lexora Research** (composite) builds a contract-review assistant for mid-market law firms. The product retrieves clauses from firm playbooks and prior work product, then drafts redline suggestions. Buyers demand auditability: every sentence must map to a sourced clause.

## Technical challenge

The team evaluated three retrieval backends before a production rollout:

1. Managed vector DB A (HNSW, cosine)
2. Self-hosted pgvector
3. Hybrid BM25 + dense (candidate)

They needed an objective comparison of **retrieval accuracy**, **ranking quality**, and **grounding failure rates** — not vendor latency slides.

## Existing workflow

- Engineers ran ad-hoc notebooks comparing Recall@5 on a 200-query gold set
- Partners reviewed answers in Google Docs with no sentence↔chunk linkage
- Embedding model and chunk size were changed independently; regressions were discovered weeks later in client pilots

## Problems

| Symptom | Impact |
|---------|--------|
| High Recall@5 but low faithfulness | Answers cited the wrong clause family |
| Dense-only miss on exact statute citations | Lexical queries underperformed |
| No shared failure taxonomy | “Hallucination” used for retrieval misses |
| Chunk size A/B without Trust Score | Partners could not quantify quality deltas |

## How RAGInspector is used

1. Instrumented the review service with the Python SDK (`pipeline_id` per vector backend).
2. Ingested the same gold queries against each backend as separate pipelines.
3. Used `/benchmark` for retrieval strategy comparison on real traces (not synthetic forecasts).
4. Used query-detail grounding to score sentence-level support for redline suggestions.
5. Used `/regression` snapshots before promoting a backend or embedding model.
6. Used BM25 vs vector metrics to decide hybrid merge weights.

## Architecture involved

```text
Review service ──SDK──► RAGInspector API
                         │
                         ▼
                   Celery analysis (NLI grounding, BM25 observability, Trust Score)
                         │
                         ▼
                   Dashboard: pipelines A/B, grounding UI, regression suite
```

Self-hosted Compose in a VPC; PHI/PII of client contracts stayed in Lexora’s network. LLM-as-judge disabled; local NLI only.

## Evaluation process

1. Freeze a 200-query gold set with expected clause IDs.
2. Run identical top_k=5 retrieval across three backends; ingest traces.
3. Wait for analysis `completed`; compare Trust Score, grounding fraction, failure class mix.
4. Tune hybrid weights using BM25 win-rate on citation-style queries.
5. Capture a regression baseline before cutover; re-run on canary week.

## Metrics collected

| Metric | Backend A | pgvector | Hybrid |
|--------|----------:|---------:|-------:|
| Mean Trust Score | 71 | 74 | **82** |
| Grounded sentence fraction | 0.68 | 0.71 | **0.84** |
| `retrieval_miss` share | 22% | 18% | **9%** |
| BM25 lexical win rate (citation queries) | — | 12% | **44%** |
| Mean analysis latency p95 (warm) | 4.8s | 4.6s | 5.2s |

## Results

Hybrid + re-chunked playbook tables won the bake-off. pgvector stayed as the store; BM25 was added as an observability-backed ranking signal in the product retrieval path. Partners accepted the grounding UI as the review surface for pilot matters.

## Engineering impact

- Replaced notebook bake-offs with a repeatable pipeline A/B + regression gate.
- Failure classes separated retrieval misses from generation hallucinations — fixed the wrong layer first.
- Embedding upgrades now require a green `/regression` run before merge.

## Business impact

- Pilot firm time-to-validate a redline dropped from ~6 min to ~2 min median.
- Two lost deals citing “unverifiable AI” were reopened after grounding demos.
- Avoided a managed-vector lock-in that would have added ~$4k/month without Trust Score gains.

## Lessons learned

1. Vector DB choice is secondary to **measurable grounding** and failure taxonomy.
2. Legal citation queries need lexical signals; dense-only Recall@5 lied.
3. Regression snapshots prevent silent quality drops when chunking or embeddings change.
4. Keep NLI local when client work product cannot leave the VPC.

## Future improvements

- Per-matter retention policies for ingested traces
- Clause-graph visualization (PRD knowledge graph) once coverage maps stabilize
- Optional SSO to firm IdP when SCIM depth graduates from experimental
