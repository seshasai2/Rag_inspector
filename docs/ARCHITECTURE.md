# RAGInspector Architecture

**Status:** Binding design decision  
**Date:** 2026-07-13  
**Audience:** Contributors, interviewers, recruiters reviewing the codebase  

---

## Decision summary

| Priority | Source of truth | Scope |
|----------|-----------------|-------|
| **1 — Hiring / portfolio** | `08_RAGInspector_PRD.md` (v1) | Production RAG pipeline debugger |
| **2 — Product heroes** | Spec v2 Trust Score + Hallucination Cost | Adopt into the v1 core loop |
| **3 — Deferred SaaS** | `08_raginspector_prd_v3_final.md` | Phase 10 only (`ROADMAP.md`) |

**Why:** A deep, correct observability core (SDK → ingest → Celery analysis → grounding UI) proves production AI engineering. A wide unfinished enterprise surface (SSO stubs, studio, investigator) weakens hiring signal.

---

## System context

```text
┌─────────────────────────┐
│  User RAG application   │
│  (Python + SDK)         │
└───────────┬─────────────┘
            │ POST /api/v1/ingest/trace
            │ X-API-Key
            ▼
┌─────────────────────────┐     ┌──────────────┐
│  FastAPI backend        │────▶│ PostgreSQL   │
│  auth · pipelines ·     │     │ traces,      │
│  queries · metrics ·    │     │ chunks,      │
│  settings · billing     │     │ users        │
└───────────┬─────────────┘     └──────────────┘
            │ Celery (analysis queue)
            ▼
┌─────────────────────────┐     ┌──────────────┐
│  Celery worker          │────▶│ Redis        │
│  grounding (NLI)        │     │ broker       │
│  BM25 · metrics ·       │     └──────────────┘
│  failure classifier     │
└─────────────────────────┘
            ▲
            │ JWT Bearer
┌───────────┴─────────────┐
│  Next.js dashboard      │
│  dashboard · queries ·  │
│  chunks · metrics ·     │
│  pipelines · settings   │
└─────────────────────────┘
```

---

## Core loop (in scope for hiring)

```text
Instrument → Ingest → Analyze → Inspect → Improve
```

| Step | Component | Responsibility |
|------|-----------|----------------|
| Instrument | `sdk/raginspector` | Decorators capture retrieve/generate latency + chunks + answer |
| Ingest | `POST /api/v1/ingest/trace` | Auth via API key, plan limits, persist trace, enqueue analysis |
| Analyze | `app.workers.tasks.run_analysis` | Grounding, BM25, RAGAS-style metrics (incl. context recall), trust score, failure class, chunk stats |
| Inspect | Frontend `/queries/[id]` | Sentence-level grounding with hover → supporting chunk highlight |
| Improve | Chunk flags + fix recommendations | Surface low-citation chunks and coverage gaps |

**Query detail grounding UX (PRD key page):** `frontend/src/components/grounding-attribution.tsx` — side-by-side answer sentences and retrieved chunks; hover/pin a sentence to highlight and scroll to its supporting chunk and show a chunk-text tooltip.

### Trust Score (hero metric)

Canonical implementation: `app/services/trust_scorer.py`.

Computed over the most recent **100** traces:

| Component | Source | Weight |
|-----------|--------|--------|
| Faithfulness | mean(`faithfulness_score`) | ×30 |
| Grounding | mean(`grounded_fraction`) | ×30 |
| Retrieval | mean(`context_precision_score`) | ×20 |
| Reliability | `(1 − hallucination_rate)` | ×20 |

Result is rounded to 1 decimal (0–100). Exposed on dashboard as `trustworthiness_score`, on pipeline stats/compare as `trust_score`, and in executive reports as `ai_trust_score`.

Per-trace `trustworthiness_score` (worker) remains a separate 60/40 faithfulness+grounding diagnostic stored on each row.

### Hallucination Cost (hero metric)

Canonical implementation: `app/services/hallucination_cost.py`.

| Input | Source |
|-------|--------|
| Hallucination rate | `is_hallucination` fraction on pipeline traces |
| Queries / month | `pipelines.queries_per_month` (default 10 000) |
| Unit cost | `pipelines.cost_per_wrong_answer_usd` (default $5) |

`monthly_cost = rate × queries_per_month × cost_per_wrong_answer_usd`

Editable via `PATCH /api/v1/pipelines/{id}` and the dashboard cost card. Multi-pipeline dashboard sums each pipeline’s estimate.

### Context recall

Canonical implementation: `app/services/context_recall.py`.

Populated on analysis complete as `QueryTrace.context_recall_score` (0–1):

| Path | When | Method |
|------|------|--------|
| Heuristic (default) | Always | 60% query-term coverage in chunks + 40% answer-sentence attribution (embedding/lexical) |
| LLM (optional) | `HF_API_TOKEN` set | Extract information needs from the query; verify each against context |

Low recall (`< 0.4`) contributes to `retrieval_miss` in the failure classifier.

### BM25 vs vector (PRD F4)

Canonical implementation: `app/services/bm25_service.py` + `bm25_metrics.py`.

| Surface | Field / endpoint |
|---------|------------------|
| Per query | `GET /queries/{id}` → `bm25_comparison` + per-chunk `bm25_score` / `similarity_score` |
| Aggregate | `GET /metrics/bm25-comparison` and dashboard `bm25_outperform_rate` |

Rule: BM25 “wins” when `max(bm25) > max(vector) + 0.15`. Hybrid recommended at ≥30% win rate over ≥10 comparable traces.

### Chunk quality (PRD F5)

Canonical implementation: `app/services/chunk_quality.py`.

Auto-flag when `retrieval_count >= 50` and `citation_rate < 0.20` (ingest + analysis + Celery beat). Heatmap UI: `/chunks` (grid + table). Summary: `GET /chunks/summary`.

List-filter indexes for queries/chunks: [`docs/INDEXES.md`](INDEXES.md) (migration `013_list_filter_indexes`).

Dashboard / query list-detail load paths are batch-oriented (Phase 6.2): no per-pipeline N+1 for Hallucination Cost; trace detail uses `selectinload`.

ML models (NLI + embeddings): lazy process cache with Celery warm-on-start — [`docs/COLD_START.md`](COLD_START.md).

List pagination: defaults and hard caps in `app/core/pagination.py` (`per_page` ≤ 100, `limit` ≤ 100, admin/audit ≤ 200).

### Core API surface (canonical)

| Method | Path | Auth |
|--------|------|------|
| POST | `/api/v1/auth/register`, `/login`, `/login/mfa`, `/refresh`, `/me` | public / JWT |
| GET | `/api/v1/auth/verify-email?token=` | public |
| POST | `/api/v1/auth/resend-verification` | public (email body) |
| GET | `/api/v1/audit-logs` | org admin + enterprise (`?action=` / `?target_type=` / `?since=`) |
| CRUD | `/api/v1/keys`, `/api/v1/pipelines` | JWT |
| POST | `/api/v1/ingest/trace` | API key (`ingest:write`) |
| GET | `/api/v1/queries`, `/api/v1/queries/{id}` | JWT |
| POST | `/api/v1/queries/{id}/reanalyze` | JWT |
| GET | `/api/v1/chunks`, `/api/v1/metrics/*` | JWT |
| GET/PUT | `/api/v1/settings` | JWT |
| * | `/api/v1/billing/*` | JWT (skeleton; SaaS later) |

**Naming note:** PRD v1/v3 sometimes say `/api/v1/traces/batch`. This repo’s canonical ingest path is `/api/v1/ingest/trace` (single-trace, SDK fire-and-forget). Batch alias may be added for compatibility; do not treat PRD path names as live OpenAPI without checking `app/api/v1/router.py`.

---

## Layering (backend)

```text
api/v1/endpoints/*   → HTTP, auth deps, status codes
services/*           → business logic (grounding, BM25, trends, queue)
workers/*            → Celery tasks (sync DB session)
models/*             → SQLAlchemy ORM
schemas/*            → Pydantic request/response
core/*               → config, security, logging
db/*                 → engines, sessions
```

**Rules:**

1. Endpoints stay thin — no metric aggregation or report math in route handlers long-term (see ROADMAP 2.2).
2. ID strategy: `String(36)` storing `str(uuid.uuid4())` everywhere (migration `010`).
3. Plan enum: `free | starter | pro | enterprise` (migration `009`; legacy `saas` → `pro`).
4. Analysis must not sit in `pending` forever if Redis/Celery is down — mark `failed` and allow `/reanalyze`.

---

## Data model (core)

| Table | Role |
|-------|------|
| `users` | Account, plan, usage counters |
| `api_keys` | Hashed keys + scopes |
| `pipelines` | Named RAG pipelines per user |
| `query_traces` | Query/answer + scores + failure + latencies |
| `retrieved_chunks` | Per-trace chunk rows |
| `grounding_results` | Sentence-level NLI outcomes |
| `chunk_stats` | Retrieval/citation aggregates |
| `analysis_jobs` | Celery job status / errors |
| `user_settings` | Ollama URL, thresholds, alerts |

Enterprise/org/SSO/MFA/audit tables exist but are **not** part of the hiring core narrative until Phase 10.

---

## Boundary list — implemented vs deferred

### Implemented (demo this)

- SDK decorator tracing + HTTP ingest
- JWT + refresh rotation + API keys
- Celery analysis: grounding, BM25, metrics, classifier, chunk stats
- Dashboard / queries / query detail / chunks / metrics / pipelines / settings
- Auth middleware + app layout session gate
- Docker Compose stack (db, redis, backend, worker, frontend, nginx)
- Week-over-week dashboard trends from real data

### Partial / experimental (do not oversell)

| Area | Reality |
|------|---------|
| Billing (Razorpay) | Usage + verify + failed-payment webhooks; live keys still required |
| Slack alerts | Wired when user Slack webhook is configured |
| Enterprise console UI | Quarantined honesty notice at `/enterprise` |
| SSO / SCIM | Google OAuth live with env creds; other IdPs/SCIM stub |
| Official RAGAS package | Custom LLM/heuristic metrics, not the `ragas` library |

### Phase 10 SaaS (shipped, scoped)

See [IMPLEMENTED.md](IMPLEMENTED.md). Includes knowledge gaps, autofix verify loop, documents/freshness, monitoring, regression, retrieval/LLM benchmarks, studio heuristics, AI Investigator (cited metrics), executive PDF, org invite/RBAC, LlamaIndex/Haystack SDK adapters, Google SSO.

---

## Deployment topology

| Environment | Notes |
|-------------|-------|
| Local / demo | `docker compose up` — see `README.md` |
| Windows host without Postgres | App may fall back to SQLite (`app/db/session.py`); **CI and production must use Postgres** |
| Production | `docker-compose.prod.yml` (ROADMAP Phase 8); TLS via nginx |

---

## Non-goals (post Phase 10)

- Claiming unpaid “enterprise-ready” without live Razorpay/IdP credentials in the demo environment
- Expanding multi-IdP SSO / full SCIM without a new roadmap revision
- Inventing Phase 11 tasks without updating `ROADMAP.md`

---

## Related docs

| Doc | Purpose |
|-----|---------|
| `ROADMAP.md` | Ordered execution contract |
| `README.md` | Quick start + SDK usage |
| `docs/DEPLOYMENT.md` | Deploy checklist |
| `docs/API_KEYS.md` | API key operations |
| OpenAPI | `http://localhost:8000/docs` |
