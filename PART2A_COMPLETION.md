# Part 2A Completion — Backend, SDK, AI Pipeline & Data Layer

**Date:** 2026-07-14  
**Status:** Complete (verified)

## Done

### Analysis pipeline
- Extracted `app/services/analysis_pipeline.py` with staged functions + latencies
- Celery `run_analysis` is a thin wrapper with configurable soft/hard time limits + retries
- Idempotent skip when already completed / fresh running lock
- Stage timings persisted to `QueryTrace.analysis_latencies_json`
- Hybrid merge observability via `merge_hybrid_rankings` (configurable weights)

### Ingest / data layer
- `app/services/ingest_service.py` owns ingest business logic
- Batch ChunkStat upsert (eliminates N+1)
- Observability fields + migration `020_trace_observability_fields.py`
- Batch endpoint calls service directly (not rate-limited endpoint wrapper)

### Redis
- Async Redis get/set for dashboard cache path (sync kept for non-async callers)
- Configurable socket timeouts

### Exceptions / config
- Domain exceptions in `app/core/exceptions.py` + FastAPI handler (no stack traces to clients)
- New Settings: Redis timeouts, analysis time limits, hybrid weights
- `.env.example` / `.env.production.example` updated

### SDK
- Persistent pooled httpx clients
- `set_context`, `trace_stage`, `trace_reranking`
- Richer payload: session/request/metadata/stage_latencies/rank_latency
- Async embedding vector capture

## Verification
- Backend unit: **253 passed**
- SDK: **36 passed**
- Ruff on touched modules: clean

## Deferred to Part 2B / later
- Full OpenAI-style embedding/vector-DB product surface (RAGInspector observes customer pipelines; it does not own them)
- Frontend token/session security
- Split mega models/schemas files
- Playwright E2E
