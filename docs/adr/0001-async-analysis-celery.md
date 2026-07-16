# ADR 0001: Async analysis via Celery

- **Status:** Accepted  
- **Date:** 2026-07

## Context

Grounding (NLI), BM25 comparison, and embedding-related work are multi-second and RAM-heavy. Callers need a low-latency ingest path for SDKs and CI.

## Decision

Persist the trace in PostgreSQL, enqueue `run_analysis` on Celery, return quickly (accepted / pending analysis). Isolate long ML work on an `analysis` queue separate from light beat/webhook tasks.

## Alternatives considered

| Option | Why rejected |
|--------|----------------|
| Inline analysis in FastAPI | Destroys p99; OOMs web replicas |
| Thread pool on API pods | Harder to warm models; couples scale of API and ML |
| Always-on GPU microservice | Cost/ops overkill for OSS self-host |

## Consequences

- Workers need model warm-on-start and low concurrency (weights per process).  
- Ingest must tolerate queue failure without losing the stored trace.  
- Ops own backlog metrics (`/api/v1/ops/metrics`, Grafana).
