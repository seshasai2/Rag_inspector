# Analysis service collaboration

How core analysis services collaborate after a trace is ingested. `analysis_pipeline` orchestrates grounding, BM25, RAGAS-style metrics, trust scoring, failure classification, and chunk quality updates.

```mermaid
flowchart LR
    IN["ingest_service<br/>persist trace + chunks"]
    Q["analysis_queue<br/>enqueue Celery task"]
    PIPE["analysis_pipeline.run"]

    G["grounding<br/>NLI sentence→chunk"]
    BM["bm25_service<br/>+ bm25_metrics"]
    CR["context_recall"]
    RAG["ragas_service<br/>faithfulness / precision"]
    TS["trust_scorer"]
    HC["hallucination_cost"]
    FC["failure_classifier"]
    CQ["chunk_quality"]
    DM["dashboard_metrics<br/>+ dashboard_cache"]

    IN --> Q --> PIPE
    PIPE --> G
    PIPE --> BM
    PIPE --> CR
    PIPE --> RAG
    PIPE --> FC
    PIPE --> CQ
    G --> TS
    RAG --> TS
    FC --> HC
    TS --> DM
    HC --> DM
```

Primary entry points:

- Ingest: `POST /api/v1/ingest/trace` → `ingest_service` → `analysis_queue`
- Worker: `run_analysis(trace_id)` → `analysis_pipeline`
- Dashboard: `GET /api/v1/metrics/dashboard` → `dashboard_metrics` (Redis TTL cache)

See also: [02-analysis-sequence.md](02-analysis-sequence.md), [12-worker-architecture.md](12-worker-architecture.md).
