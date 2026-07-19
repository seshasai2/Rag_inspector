# Hiring notes

Short talking points derived from this repository. For the full engineering narrative, interview Q&A, and assessment, use **[PROJECT_GUIDE.md](../PROJECT_GUIDE.md)**.

## Resume bullets (pick 3–4)

- Built an end-to-end **RAG observability platform**: Python SDK instrumentation → FastAPI ingest → Celery analysis workers → Next.js grounding UI with sentence↔chunk attribution.
- Implemented **local NLI grounding** and retrieval diagnostics (BM25 vs vector, failure classification, Trust Score aggregation) with worker cold-start and fallback behavior.
- Hardened for production: Docker Compose prod (no bind mounts, resource limits), TLS nginx overlay, fail-closed config validation, structured logs with **X-Request-ID**, backup/restore runbook.
- Shipped developer UX: Make/PowerShell setup, demo seed, health/readiness probes, pagination/cache/backlog ops endpoints, CI lint/typecheck.

## 60-second demo

1. Seed login → open a hallucinated vs grounded query on `/queries/[id]`.
2. Hover an ungrounded sentence — no supporting chunk highlight.
3. Mention async path: ingest returns before analysis; worker writes results.
4. Show honesty: Razorpay/live SSO need real credentials; see [IMPLEMENTED.md](IMPLEMENTED.md) and [EXPERIMENTAL.md](EXPERIMENTAL.md).

## Links

- [PROJECT_GUIDE.md](../PROJECT_GUIDE.md) — canonical guide + interview prep
- [FAQ.md](FAQ.md)
- [adr/](adr/) — architecture decision records
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [demo/](demo/) — longer walkthroughs
