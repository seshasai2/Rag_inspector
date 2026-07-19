# Architecture diagrams

Mermaid diagrams for RAGInspector system design. Start with [PROJECT_GUIDE.md](../../PROJECT_GUIDE.md) for the full engineering narrative, then [ARCHITECTURE.md](../ARCHITECTURE.md) for the binding product scope, then the diagrams below for C4 views and operational flows.

## Sequence flows (core loop)

| File | Flow |
|------|------|
| [01-ingest-sequence.md](01-ingest-sequence.md) | SDK → ingest → Celery enqueue |
| [02-analysis-sequence.md](02-analysis-sequence.md) | Worker analysis pipeline |
| [03-dashboard-sequence.md](03-dashboard-sequence.md) | Query detail grounding UI |

## C4 and structural views

| File | View |
|------|------|
| [04-system-diagram.md](04-system-diagram.md) | System context (users + external systems) |
| [05-container-diagram.md](05-container-diagram.md) | Deployable containers (API, worker, DB, Redis, UI) |
| [06-component-diagram.md](06-component-diagram.md) | Backend package components |
| [07-service-diagram.md](07-service-diagram.md) | Analysis service collaboration |

## Cross-cutting flows

| File | Flow |
|------|------|
| [08-auth-flow.md](08-auth-flow.md) | Register, login, MFA, SSO, API keys |
| [09-request-flow.md](09-request-flow.md) | Middleware → auth → cache → handler |
| [10-deployment-diagram.md](10-deployment-diagram.md) | Kubernetes / Compose production topology |
| [11-database-er.md](11-database-er.md) | Core ER model |
| [12-worker-architecture.md](12-worker-architecture.md) | Celery analysis vs default workers |
| [13-queue-architecture.md](13-queue-architecture.md) | Redis queues, job states, backlog |

## Related engineering docs

- [PROJECT_GUIDE.md](../../PROJECT_GUIDE.md) — canonical overview
- [API.md](../API.md) — OpenAPI entry points and auth
- [WORKER.md](../WORKER.md) — concurrency and backlog
- [DEPLOYMENT.md](../DEPLOYMENT.md) — runbooks for local and prod
- [engineering/](../engineering/) — coding standards, scaling, security, performance
