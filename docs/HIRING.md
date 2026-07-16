# Hiring notes (Phase 9.6)

Derived from this repository — use only claims you can defend from code.

## Resume bullets (pick 3–4)

- Built an end-to-end **RAG observability platform**: Python SDK instrumentation → FastAPI ingest → Celery analysis workers → Next.js grounding UI with sentence↔chunk attribution.
- Implemented **local NLI grounding** and retrieval diagnostics (BM25 vs vector, failure classification, Trust Score aggregation) with worker cold-start and fallback behavior.
- Hardened for production: Docker Compose prod (no bind mounts, resource limits), TLS nginx overlay, fail-closed config validation, structured logs with **X-Request-ID**, backup/restore runbook.
- Shipped developer UX: Make/PowerShell setup, demo seed, health/readiness probes, pagination/cache/backlog ops endpoints, CI lint/typecheck.

## Talking points (60-second demo)

1. Seed login → open a hallucinated vs grounded query on `/queries/[id]`.
2. Hover an ungrounded sentence — no supporting chunk highlight.
3. Mention async path: ingest returns before analysis; worker writes results.
4. Show honesty: Razorpay/live SSO need real credentials; see [IMPLEMENTED.md](IMPLEMENTED.md).

## Interview Q&A

**Q: Why Celery instead of analyzing inline?**  
A: Ingest latency stays low; ML models are heavy; retries and queues isolate API from worker crashes. See `analysis_queue.py` + `run_analysis`.

**Q: What if Redis is down at ingest?**  
A: Trace is stored; enqueue failure is logged; status fails closed; client can `POST .../reanalyze`.

**Q: How do you avoid fake enterprise demos?**  
A: Core nav excludes Enterprise Console; `/enterprise` redirects; stubs listed in `EXPERIMENTAL.md`.

**Q: Where is Trust Score computed?**  
A: Aggregate scorer `trust_scorer.py` over recent traces; per-trace diagnostic from the worker.

**Q: Production secrets?**  
A: Compose `${VAR:?required}` plus `validate_production_settings()` on API lifespan and Celery worker init.

## Links

- [README.md](../README.md)
- [HIRING_SIGNAL.md](HIRING_SIGNAL.md) — checklist scorecard
- [FAQ.md](FAQ.md)
- [adr/](adr/) — architecture decision records
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [ROADMAP.md](../ROADMAP.md)
