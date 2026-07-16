# Backend component diagram (C4 Level 3)

Internal structure of the FastAPI backend and worker process. Boundaries follow the existing package layout: `api` → `services` → `repositories` / `models`, with Celery tasks calling the same analysis services.

```mermaid
flowchart TB
    subgraph API["backend/app"]
        EP["api/v1/endpoints/*"]
        DEPS["api/deps.py<br/>JWT · API key · roles"]
        CORE["core/<br/>config · security · rate_limit<br/>pagination · exceptions"]
        SVC["services/<br/>ingest · grounding · trust_scorer<br/>hallucination_cost · dashboard_metrics<br/>analysis_pipeline · analysis_queue"]
        REPO["repositories/"]
        MODELS["models/models.py"]
        DB["db/session.py"]
    end

    subgraph Worker["workers/"]
        CELERY["celery_app.py"]
        TASKS["tasks.py<br/>run_analysis"]
        FRESH["freshness_worker.py"]
        MON["monitoring_worker.py"]
    end

    EP --> DEPS
    EP --> SVC
    DEPS --> CORE
    SVC --> REPO
    SVC --> MODELS
    REPO --> DB
    MODELS --> DB
    TASKS --> SVC
    CELERY --> TASKS
    CELERY --> FRESH
    CELERY --> MON
```

| Layer | Responsibility |
|-------|----------------|
| Endpoints | HTTP contracts, auth dependency injection, SlowAPI limits |
| Services | Domain logic (ingest, analysis, metrics, SSO helpers) |
| Repositories | Optional query helpers for pipelines and list filters |
| Workers | Async analysis and beat jobs; share service code with API |

See also: [07-service-diagram.md](07-service-diagram.md), [FOLDER_STRUCTURE.md](../engineering/FOLDER_STRUCTURE.md).
