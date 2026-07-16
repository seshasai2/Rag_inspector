# Celery worker architecture

Analysis and scheduled maintenance run in Celery workers that share application service code with the API. Analysis workers keep ML model concurrency low; default-queue workers handle lighter beat and webhook tasks.

```mermaid
flowchart TB
    API["FastAPI API"]
    REDIS[("Redis broker")]
    BEAT["Celery Beat"]

    subgraph AnalysisWorker["Worker: -Q analysis --concurrency 1-2"]
        RUN["tasks.run_analysis"]
        WARM["warm ML models on start<br/>NLI + embeddings"]
        PIPE["analysis_pipeline"]
    end

    subgraph DefaultWorker["Worker: -Q celery --concurrency 4"]
        WH["webhook deliveries"]
        CQ["chunk quality scan"]
        FR["document freshness"]
        MO["monitoring / alerts"]
    end

    PG[("PostgreSQL")]

    API -->|"enqueue run_analysis"| REDIS
    BEAT -->|"periodic tasks"| REDIS
    REDIS --> AnalysisWorker
    REDIS --> DefaultWorker
    WARM --> RUN --> PIPE --> PG
    WH --> PG
    CQ --> PG
    FR --> PG
    MO --> PG
```

| Setting | Guidance |
|---------|----------|
| `worker_prefetch_multiplier` | `1` — avoid hoarding long ML jobs |
| `task_acks_late` | `true` — requeue on worker crash |
| `WARM_ML_MODELS_ON_WORKER_START` | `true` on analysis workers |
| Horizontal scale | Prefer more analysis replicas over concurrency > 2 |

Backlog visibility: `GET /api/v1/ops/backlog` and Prometheus `GET /api/v1/ops/metrics`.

See also: [WORKER.md](../WORKER.md), [COLD_START.md](../COLD_START.md), [13-queue-architecture.md](13-queue-architecture.md).
