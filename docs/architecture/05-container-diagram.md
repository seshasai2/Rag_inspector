# Container diagram (C4 Level 2)

Runtime containers that make up a typical Docker Compose or Kubernetes deployment of RAGInspector. Each box is an independently deployable process with its own scaling and health checks.

```mermaid
flowchart TB
    user["Dashboard User<br/>Browser"]

    subgraph raginspector["RAGInspector"]
        web["Next.js Frontend<br/>Node 20 / Next 15"]
        api["FastAPI Backend<br/>Python / Uvicorn"]
        worker["Celery Worker<br/>run_analysis · grounding"]
        beat["Celery Beat<br/>freshness · chunk scan"]
        pg[("PostgreSQL 16")]
        redis[("Redis 7<br/>broker + cache")]
    end

    user -->|HTTPS JWT| web
    web -->|/api/v1 JSON| api
    api --> pg
    api --> redis
    worker --> redis
    worker --> pg
    beat --> redis
```

Local ports (Compose): API `8000`, UI `3000`, Postgres `5432`, Redis `6379`. Production images and Helm charts live under `infrastructure/`.

See also: [10-deployment-diagram.md](10-deployment-diagram.md), [WORKER.md](../WORKER.md).
