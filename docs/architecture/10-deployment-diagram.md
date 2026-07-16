# Deployment topology

Recommended production-shaped topology using Kubernetes (or Compose Prod) with separate API, worker, and beat workloads, plus managed Postgres and Redis. Observability scrapes Prometheus metrics from the API.

```mermaid
flowchart TB
    subgraph Edge
        LB["Load balancer / Ingress<br/>TLS termination"]
    end

    subgraph Cluster["Kubernetes namespace: raginspector"]
        FE["Deployment: frontend<br/>Next.js replicas ≥ 2"]
        API["Deployment: backend<br/>Uvicorn / Gunicorn replicas ≥ 2"]
        W["Deployment: worker-analysis<br/>concurrency 1–2"]
        WD["Deployment: worker-default<br/>queue celery"]
        BEAT["Deployment: beat<br/>replicas = 1"]
        PROM["Prometheus + Grafana<br/>optional overlay"]
    end

    subgraph Data["Managed data plane"]
        PG[("PostgreSQL 16<br/>Alembic migrations")]
        RD[("Redis 7<br/>broker + cache")]
    end

    Clients["Browsers + SDK clients"] --> LB
    LB --> FE
    LB --> API
    FE --> API
    API --> PG
    API --> RD
    W --> RD
    W --> PG
    WD --> RD
    WD --> PG
    BEAT --> RD
    PROM --> API
```

| Workload | Health | Scale signal |
|----------|--------|--------------|
| `backend` | `/live`, `/api/v1/ops/ready` | CPU RPS + p95 latency |
| `worker-analysis` | process liveness + backlog drain | `celery_queue_depths.analysis` |
| `worker-default` | process liveness | webhook / beat task lag |
| `frontend` | HTTP `/` | concurrent sessions |
| `beat` | single replica | N/A (do not HPA) |

Compose local stack: `make bootstrap`. Production compose: `make up-prod`. Helm: `infrastructure/kubernetes` + [`HELM.md`](../HELM.md).

See also: [KUBERNETES.md](../KUBERNETES.md), [AUTOSCALING.md](../AUTOSCALING.md).
