# Architecture walkthrough (demo)

Narrated architecture for interviews and customer demos. Pair with Mermaid files under `docs/architecture/`.

## Storyboard (8 minutes)

### 1. System context (1 min)

Show [04-system-diagram.md](../architecture/04-system-diagram.md): customer RAG app + SDK, dashboard users, IdP, optional HF/LLM, Slack, Razorpay.

**Line:** “We sit beside your RAG stack — we do not replace retrieval.”

### 2. Containers (1 min)

[05-container-diagram.md](../architecture/05-container-diagram.md): Next.js, FastAPI, Celery worker/beat, Postgres, Redis.

**Line:** “API stays thin; ML runs in workers with low concurrency.”

### 3. Core loop sequence (3 min)

1. [01-ingest-sequence.md](../architecture/01-ingest-sequence.md) — API key ingest, persist, enqueue.
2. [02-analysis-sequence.md](../architecture/02-analysis-sequence.md) — grounding, BM25, metrics.
3. [03-dashboard-sequence.md](../architecture/03-dashboard-sequence.md) — sentence ↔ chunk UX.

### 4. Queues & workers (2 min)

[12-worker-architecture.md](../architecture/12-worker-architecture.md) and [13-queue-architecture.md](../architecture/13-queue-architecture.md): `analysis` vs `celery`, prefetch 1, warm models, backlog endpoints.

### 5. Auth & deploy (1 min)

[08-auth-flow.md](../architecture/08-auth-flow.md) JWT vs API keys; [10-deployment-diagram.md](../architecture/10-deployment-diagram.md) K8s topology.

## Talking points that land

| Topic | Honest detail |
|-------|----------------|
| Trust Score | Weighted faithfulness, grounding, precision, hallucination rate over last 100 traces |
| Hallucination Cost | `rate × queries_per_month × cost_per_wrong_answer` |
| Cold start | NLI/embeddings warmed on worker start — see COLD_START.md |
| Failure modes | Broker down → trace stored; reanalyze later |

## Source map

| Claim | Code / doc |
|-------|------------|
| Binding architecture | `docs/ARCHITECTURE.md` |
| Models | `backend/app/models/models.py` |
| Pipeline | `backend/app/services/analysis_pipeline.py` |
| Worker ops | `docs/WORKER.md` |
