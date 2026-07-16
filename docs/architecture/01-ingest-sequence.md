# Ingest sequence (SDK → API → queue)

```mermaid
sequenceDiagram
    autonumber
    participant App as User RAG app
    participant SDK as raginspector SDK
    participant API as FastAPI /ingest/trace
    participant DB as PostgreSQL
    participant Redis as Redis broker
    participant W as Celery worker

    App->>SDK: retrieve() / generate()
    SDK->>API: POST /api/v1/ingest/trace (X-API-Key)
    API->>DB: insert QueryTrace + chunks + AnalysisJob
    API->>Redis: enqueue run_analysis(trace_id)
    API-->>SDK: 202 + trace_id
    Note over Redis,W: If broker down, trace stored; status failed; reanalyze later
    W->>Redis: consume analysis queue
    W->>DB: load trace, write grounding + metrics
    W->>DB: update AnalysisJob completed
```

See also: `backend/app/api/v1/endpoints/ingest.py`, `backend/app/services/analysis_queue.py`, `backend/app/workers/tasks.py`.
