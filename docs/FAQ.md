# FAQ

## Product

### What problem does RAGInspector solve?
RAG apps fail quietly: wrong chunks, weak grounding, or confident hallucinations. Teams see a bad answer but not *which stage* broke. RAGInspector instruments retrieval + generation, analyzes traces asynchronously, and shows sentence↔chunk attribution so you can fix the pipeline in minutes.

### Who is it for?
ML / backend engineers and platform teams shipping RAG in production (support bots, internal knowledge, search+answer products)—especially self-hosted or OSS-first shops.

### How is this different from an LLM observability vendor?
Vendors often center prompt/LLM spans and dashboards. RAGInspector centers **retrieval + grounding diagnostics** (BM25 vs vector, NLI grounding, Trust Score, failure class) with a free SDK and Compose stack—no paid SaaS required to run.

### What are success metrics?
- Time-to-root-cause for a bad answer (target: &lt; 30 seconds for a seeded trace).  
- Trust Score / grounded fraction trends after fixes.  
- Hallucination-cost signal when customers set cost-per-wrong-answer.  
- Analysis backlog under control (ops metrics).

## Setup

### Why can't I just `docker compose up` without `.env`?
Production compose **fail-closes** on missing secrets. Locally, copy `.env.example` → `.env` and set `SECRET_KEY` (≥32 characters). Windows: `.\scripts\setup.ps1` then `.\scripts\bootstrap.ps1`.

### Demo login?
After seed: `demo@example.com` / `DemoPass123!` on http://localhost:3000

### Do I need Razorpay / Google OAuth?
No. Billing and SSO are optional. See [EXPERIMENTAL.md](EXPERIMENTAL.md) and [IMPLEMENTED.md](IMPLEMENTED.md).

## Architecture

### Why Celery instead of analyzing inside the HTTP request?
NLI and embeddings are multi-second and memory-heavy. Blocking the API would destroy latency. Ingest stores the trace and enqueues analysis; the worker writes results. See [adr/0001-async-analysis-celery.md](adr/0001-async-analysis-celery.md).

### What if Redis/Celery is down at ingest time?
The trace is still stored. Enqueue failure is logged; analysis status fails closed; you can re-analyze later. Clients should treat ingest as durable persistence + best-effort queue.

### Is SAML/SCIM production-ready?
Not as GA. Partial surfaces are honesty-gated. Do not demo them as finished enterprise features.

## Security & ops

### Where do secrets live?
`.env` (gitignored). Templates: `.env.example`, `.env.production.example`. Guide: [SECRETS.md](SECRETS.md), [../SECURITY.md](../SECURITY.md).

### How do I get metrics and alerts?
`make up-obs` (or deploy with observability overlay). Prometheus + Grafana with exporters and alert rules under `infra/observability/`.

## Hiring interviews

### Where should I start in a live review?
[docs/HIRING.md](HIRING.md) · [docs/HIRING_SIGNAL.md](HIRING_SIGNAL.md) · seeded grounding UI on `/queries/[id]`.
