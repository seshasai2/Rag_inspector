# RAGInspector — Project Guide

**Canonical engineering document** for this repository.  
If you are new to the codebase, start here. Architecture diagrams, ADRs, and ops runbooks remain the detailed sources of truth for their domains; this guide ties them together without inventing features.

| Audience | What you should get |
|----------|---------------------|
| New engineers | Mental model, folder map, how to run and debug |
| Hiring managers / interviewers | What is real, what is scoped, what trade-offs were made |
| Open-source contributors | Boundaries, honesty layer, where to change code |
| Technical leads | Failure modes, performance class, scaling posture |

Related: [README.md](README.md) · [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · [docs/adr/](docs/adr/) · [docs/IMPLEMENTED.md](docs/IMPLEMENTED.md) · [docs/EXPERIMENTAL.md](docs/EXPERIMENTAL.md) · [docs/engineering/PERFORMANCE.md](docs/engineering/PERFORMANCE.md)

---

## Executive Summary

RAGInspector is a self-hosted **RAG pipeline debugger**: instrument a Python app with an SDK, ingest traces into FastAPI, analyze them asynchronously with Celery (sentence-level NLI grounding, BM25 vs vector comparison, failure classification, Trust Score), and inspect attribution in a Next.js dashboard. It is built for teams that need retrieval-and-grounding diagnostics without buying a closed LLM-ops SaaS. Core loop is production-shaped (Compose, Helm charts, CI, Prometheus). Enterprise IdP surfaces (SAML/SCIM) and live billing are partial or experimental and are labeled as such.

---

## Elevator Pitch

When a RAG answer is wrong, you usually cannot tell whether retrieval missed or the model invented. RAGInspector records the retrieve/generate path, runs grounding analysis in workers, and shows which answer sentences are supported by which chunks — so you can fix the pipeline instead of guessing from logs.

---

## Product Vision

Detect → Explain → Recommend → Verify.

The product exists to make RAG failures **inspectable**: not another chat UI, and not a generic span viewer. The differentiator is grounded sentence↔chunk attribution plus retrieval diagnostics (BM25 vs dense ranking, failure class, Trust Score / hallucination-cost signal), runnable on free OSS infrastructure.

Hiring-facing scope prioritizes a deep correct core over unfinished enterprise width. See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) and [ROADMAP.md](ROADMAP.md).

---

## Business Problem

| Dimension | Detail |
|-----------|--------|
| **Problem** | Production RAG fails silently. Wrong chunks, weak ranking, and fluent hallucinations look the same in application logs. |
| **Who feels it** | ML, backend, and platform engineers shipping support bots, internal knowledge Q&A, and search+answer products. |
| **Cost** | Wrong answers drive escalations, refunds, compliance risk, and eng time spent on guesswork. Case studies use customer-supplied unit costs (e.g. $/wrong answer × volume) via Hallucination Cost — not a fixed industry number invented by this repo. |
| **Success** | Root-cause a bad seeded answer in under ~30 seconds; trend Trust Score / grounded fraction; keep analysis backlog visible to ops. |

---

## Existing Solutions

| Tool class | Strengths | Gaps relative to this project |
|------------|-----------|-------------------------------|
| Langfuse / Helicone / generic LLM observability | Strong prompt/span tracing, SaaS polish | Rarely centers sentence↔chunk grounding, BM25 vs dense comparison, or Trust Score tied to wrong-answer cost |
| RAGAS / offline eval libs | Solid metrics libraries | Not a full ingest → worker → dashboard product loop |
| Homegrown notebooks + logging | Flexible | No shared UI, weak ops, hard to institutionalize |
| Full enterprise IdP platforms | SSO/SCIM mature | Orthogonal; this repo does **not** claim to replace them |

**Why build this:** Own the debugger loop end-to-end (SDK → async analysis → UI) with an honesty layer for unfinished enterprise pieces, and keep the stack self-hostable (Docker Compose, Postgres, Redis, Celery).

---

## Target Users

| User | Benefit |
|------|---------|
| ML / Applied AI engineer | Sees grounding and failure class instead of only BLEU-style offline scores |
| Backend / platform engineer | API keys, queues, readiness, Compose/Helm-shaped deploy |
| Eng manager / tech lead | Trust Score + optional dollarized hallucination cost for prioritization |
| OSS contributor / evaluator | Clone → bootstrap → seed → inspect without paid SaaS |

---

## Core Features

Do not treat the table in [docs/IMPLEMENTED.md](docs/IMPLEMENTED.md) as marketing. Below is *why* the live surfaces matter.

### Instrumentation (Python SDK)

Decorators and framework adapters (LangChain / LlamaIndex / Haystack) capture retrieve/generate latency, chunks, and answers. Without cheap instrumentation, nobody instruments production. The SDK posts to ingest with `X-API-Key`.

### Async analysis

Ingest returns quickly (accepted / pending). Celery workers run NLI grounding, BM25 comparison, metrics, failure classification, and Trust-related fields. Blocking that work inside HTTP would destroy p99 and couple API scale to model RAM ([ADR 0001](docs/adr/0001-async-analysis-celery.md)).

### Sentence-level grounding UI

Query detail (`/queries/[id]`) links answer sentences to supporting chunks. This is the product’s “show me the evidence” moment — the feature most interviewers should click first.

### BM25 vs vector

Surfaces whether lexical retrieval would have ranked differently from the dense path. Useful when hybrid retrieval is under debate.

### Failure classification + Trust Score + Hallucination Cost

Failure types separate retrieval misses from generation issues. Aggregate Trust Score (weighted faithfulness / grounding / retrieval / reliability over recent traces) gives a dashboard hero metric. Hallucination Cost turns rate × volume × $/wrong-answer into a leadership-facing number — inputs are pipeline settings, not invented ROI.

### Knowledge gaps, autofix, monitoring, regression, documents

Phase 10 surfaces exist as **scoped** product features (routes + services + tests). They use measured or heuristic data — not fabricated forecasts. See [IMPLEMENTED.md](docs/IMPLEMENTED.md).

### Auth & tenancy

JWT + refresh revoke, optional MFA TOTP (login-gated), hashed API keys with scopes, org RBAC and plan gates. Google SSO works when OAuth env is set. SAML/SCIM are experimental stubs ([EXPERIMENTAL.md](docs/EXPERIMENTAL.md)).

### Ops surface

`/live`, `/api/v1/ops/ready`, Prometheus metrics, Compose observability overlay, Helm chart, backup/DR docs. Enough to run seriously self-hosted; not a claim of multi-region SaaS GA.

---

## End-to-End Workflow

### Happy path (demo seed)

1. **Bootstrap** — `make bootstrap` (or Windows `scripts/bootstrap.ps1` + verify-ports compose). Migrate + seed.
2. **Login** — `demo@example.com` / `DemoPass123!` on the UI.
3. **Instrument** (production path) — app uses SDK with API key → `POST /api/v1/ingest/trace`.
4. **Persist** — FastAPI validates key/plan limits, writes `QueryTrace` + chunks to PostgreSQL, enqueues `run_analysis`.
5. **Analyze** — Celery worker on queue `analysis` runs staged pipeline (`analysis_pipeline.py`): grounding, BM25, metrics, failure class, trust fields; updates job status.
6. **Inspect** — Dashboard loads query detail; grounding component highlights sentence↔chunk links.
7. **Monitor** — Prometheus scrapes `/api/v1/ops/metrics`; backlog/queue depth for ops; optional Grafana.

### Request flow (short)

```text
SDK ──X-API-Key──► Nginx? ──► FastAPI ingest
                              ├─► PostgreSQL (durable trace)
                              └─► Redis/Celery (best-effort enqueue)
                                        │
                                        ▼
                                 Worker analysis
                                        │
                                        ▼
                              Next.js GET /queries/{id}
```

If enqueue fails, the trace remains stored; status fails closed; client can `POST .../reanalyze`.

---

## Architecture

```text
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  RAG app + SDK  │────►│   FastAPI    │────►│ PostgreSQL  │
└─────────────────┘     │  (+ Nginx)   │     │ (+ pgvector │
                        └──────┬───────┘     │   image)    │
                               │             └─────────────┘
                               ▼
                        ┌──────────────┐
                        │ Redis broker │
                        │ + cache      │
                        └──────┬───────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
        Celery worker    Celery beat      analysis queue
        (NLI / BM25)     (schedules)      (acks_late)
              │
              ▼
        Next.js dashboard
```

| Layer | Role |
|-------|------|
| **Frontend** | Next.js 15 App Router; TanStack Query; grounding UI; JWT session cookies |
| **Backend** | FastAPI modular monolith: `api` / `services` / `workers` / `models` |
| **Workers** | Celery; low concurrency; model warm-on-start |
| **Database** | PostgreSQL 16; Alembic-owned schema |
| **Caching** | Redis TTL for dashboard aggregates |
| **Queues** | `analysis` (ML) vs `celery` (light / beat / webhooks) |
| **Storage** | Postgres primary; object storage not required for core loop |
| **Infrastructure** | Docker Compose (dev/prod/test/obs); Helm under `infrastructure/` |
| **Monitoring** | structlog + request IDs; Prometheus RED; Grafana provisioning |
| **Deployment** | Compose first; K8s via Helm (cluster install not assumed verified on every host) |

Diagram pack: [docs/architecture/](docs/architecture/). Narrative: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## Folder Structure

```text
backend/           FastAPI app, services, Celery workers, Alembic, tests
frontend/          Next.js dashboard + Vitest + Playwright e2e
sdk/               Python tracer + framework integrations
docs/              Architecture, ADRs, ops, case studies, demos, engineering
infrastructure/    Helm / Kubernetes / Terraform guidance
infra/             Prometheus / Grafana assets
loadtests/         k6, Locust, bench harnesses + artifacts
nginx/             Reverse proxy configs
docker/            DB init and image helpers
examples/          Minimal SDK usage
scripts/           Bootstrap, backup, release validation
```

| Folder | Why it exists |
|--------|----------------|
| `backend/app/services/` | Domain logic lives here — not in fat route handlers (ongoing cleanup) |
| `backend/app/workers/` | Celery app + tasks; analysis should stay thin wrappers over services |
| `backend/migrations/` | Schema history; Postgres is migration-owned |
| `frontend/src/app/(app)/` | Authenticated product pages |
| `docs/adr/` | Decision records with alternatives |
| `docs/case-studies/` | Realistic engineering narratives (not feature ads) |
| `docs/demo/` | Click-paths for demos |
| `loadtests/artifacts/` | Evidence from verification runs — keep honest |

Placement rules: [docs/engineering/FOLDER_STRUCTURE.md](docs/engineering/FOLDER_STRUCTURE.md).

---

## Technology Stack

### FastAPI (API)

| | |
|--|--|
| **What** | Async Python API framework |
| **Why** | Fits asyncio SQLAlchemy, clear OpenAPI, low ceremony for a modular monolith |
| **Solves** | Typed ingest/auth/metrics surface with production middleware hooks |
| **Pros** | Speed of delivery, native async, good typing story |
| **Cons** | Easy to grow fat endpoints; discipline required |
| **Perf** | Ingest path stays light because ML is offloaded |
| **Security** | Pair with TrustedHost, CORS lockdown, rate limits, disabled OpenAPI in prod |
| **Scale** | Horizontal API replicas behind Nginx; state in Postgres/Redis |
| **Maintenance** | Pydantic Settings + Alembic keep config/schema explicit |
| **Seen in** | Many modern Python platforms (internal APIs, ML services) |

### Celery + Redis (workers / broker)

| | |
|--|--|
| **What** | Distributed task queue + broker/cache |
| **Why** | Mature, Compose-friendly, separates ML jobs from HTTP |
| **Solves** | Retries, `acks_late`, separate queues, beat schedules |
| **Pros** | Well-understood ops; Redis doubles as cache/denylist |
| **Cons** | Redis SPOF in single-Compose; visibility needs metrics |
| **Perf** | Prefetch 1 + concurrency 1–2 for ML workers |
| **Security** | Auth Redis in prod; don’t expose broker publicly |
| **Scale** | More worker pods, not huge concurrency |
| **Enterprise examples** | Common pattern for report/ML offload in Django/FastAPI shops |

### PostgreSQL 16 (+ pgvector image)

| | |
|--|--|
| **What** | Relational system of record |
| **Why** | Traces, users, orgs, jobs need transactions and migrations |
| **Solves** | Durable ingest even when queue is down |
| **Pros** | Mature tooling, Alembic, indexes documented |
| **Cons** | Heavier than a pure document store for schemaless dumps |
| **Perf** | Connection pooling; watch dashboard aggregate queries (hence Redis cache) |
| **Security** | Credentials via env; least-privilege DB users in real prod |
| **Note** | Image includes pgvector; product path for vector search is not the primary demo loop — grounding uses local NLI in workers |

### Next.js 15 (UI)

| | |
|--|--|
| **What** | React App Router dashboard |
| **Why** | Fast UI iteration, SSR/standalone Docker story, TypeScript |
| **Solves** | Auth-gated product surfaces and grounding visualization |
| **Pros** | Ecosystem, Playwright e2e |
| **Cons** | Framework churn; keep business logic in API |
| **Security** | Never put secrets in `NEXT_PUBLIC_*` |

### sentence-transformers / local NLI

| | |
|--|--|
| **What** | Local cross-encoder / NLI for grounding |
| **Why** | Default path without paid LLM judges ([ADR 0004](docs/adr/0004-local-nli-over-cloud-judge.md)) |
| **Solves** | Deterministic-enough CI/demo grounding |
| **Cons** | Cold start + RAM; heuristic fallbacks when models fail |
| **Scale** | Memory-bound; horizontal workers |

### Docker Compose / Helm

Compose is the primary local and self-host path. Helm charts exist for Kubernetes adopters. Kubernetes is not required to evaluate the product.

### Prometheus / Grafana

RED metrics, queue depth, analysis backlog, JWT denylist fail-open counter. Optional OTel extras (`requirements-otel.txt`) are fail-open bootstrap — not a claim of full OTLP production maturity.

---

## Alternatives Considered

Only alternatives that actually applied to this repo:

### FastAPI instead of Django

| | |
|--|--|
| Django advantages | Batteries-included admin, ORM maturity |
| Django disadvantages | Heavier for async API + separate Next.js UI |
| **Choice** | FastAPI + SQLAlchemy + separate SPA |
| Better choice for Django | Heavy server-rendered admin product with Django templates |

### PostgreSQL instead of MongoDB

| | |
|--|--|
| Mongo advantages | Flexible documents for traces |
| Mongo disadvantages | Weaker relational integrity for orgs/members/billing/jobs |
| **Choice** | Postgres as system of record |
| Better choice for Mongo | Pure event dump with minimal joins |

### Redis (+ Celery) instead of Kafka

| | |
|--|--|
| Kafka advantages | Huge throughput, replay |
| Kafka disadvantages | Ops cost for OSS self-host of this size |
| **Choice** | Redis broker is enough for analysis backlog |
| Better choice for Kafka | Multi-tenant ingest at very high sustained event rates |

### Celery instead of Temporal

| | |
|--|--|
| Temporal advantages | Workflow durability, visible histories |
| Temporal disadvantages | Extra cluster; steeper for Compose-first OSS |
| **Choice** | Celery + Postgres job rows + reanalyze |
| Better choice for Temporal | Complex multi-day human-in-the-loop workflows |

### Docker Compose instead of Kubernetes-only

| | |
|--|--|
| K8s advantages | HPA, scheduling, multi-node |
| K8s disadvantages | Barrier for first eval |
| **Choice** | Compose default; Helm optional |
| Better choice for K8s-first | Platform teams already standardized on clusters |

### Next.js instead of Vue/Svelte

Team familiarity and App Router for a dense dashboard. Not a claim that Vue is inferior — switching would be cosmetic for the hiring core.

### Local NLI instead of GPT-as-judge default

Cost, rate limits, and CI nondeterminism. Optional HF/Ollama paths exist when configured.

---

## Engineering Decisions

Summarized from ADRs and [DESIGN_DECISIONS.md](docs/engineering/DESIGN_DECISIONS.md):

1. **Async analysis** — Gained API latency isolation; sacrificed immediate results on ingest response.
2. **Dual auth (JWT + API keys)** — Fits browsers and SDKs; mTLS deferred for OSS ops cost.
3. **VARCHAR(36) UUID strings** — Cross-dialect tests (SQLite + Postgres); slightly wider indexes.
4. **Split queues** — Protects light tasks from ML starvation; workers must subscribe correctly.
5. **Hero metrics** — Trust Score + Hallucination Cost for product clarity; risk of over-focusing on a single number.
6. **Heuristic context recall default** — Works offline; LLM path optional.
7. **Low worker concurrency** — Avoids OOM; scale out with replicas.
8. **OpenAPI disabled in production** — Smaller attack surface; use collections for clients.
9. **Dashboard Redis cache** — Faster reads; brief staleness.
10. **Experimental honesty layer** — Credibility over fake GA ([ADR 0005](docs/adr/0005-experimental-honesty-layer.md)).

What was sacrificed: IdP-complete enterprise SaaS polish, perfect Clean Architecture everywhere, whole-monorepo coverage %.  
What was gained: A demoable, testable RAG debugger with production-shaped ops and honest scope.

---

## Data Flow

```text
Trace payload
  → API key auth + plan quotas
  → QueryTrace + RetrievedChunks (Postgres)
  → AnalysisJob + Celery message
  → Worker stages write GroundingResults / scores / failure_type / latencies JSON
  → Dashboard metrics endpoints (often Redis-cached aggregates)
  → UI renders grounding + Trust / cost cards
```

Audit events and optional webhooks fire from worker/API paths where configured. Weekly/executive reports read aggregated metrics — they do not invent series.

---

## Request Lifecycle

### Ingest (`POST /api/v1/ingest/trace`)

1. Rate limit / API key validation / scope check  
2. Resolve pipeline + org entitlements  
3. Persist trace + chunks (batch ChunkStat where applicable)  
4. Enqueue `run_analysis` (failure → log + failed analysis status; data kept)  
5. Return accepted with trace id  

### Analysis (`run_analysis`)

1. Claim job (idempotent skip if completed / fresh lock)  
2. Staged pipeline with per-stage timings  
3. Persist results; mark completed / failed  
4. Optional Slack alert hooks  

### Dashboard read

1. JWT (or session cookie path) → user + org  
2. Pipeline ACL  
3. Metrics/detail queries; Redis cache headers when hit  

### Auth login

1. Credentials → bcrypt verify  
2. MFA gate if enrolled  
3. Issue access + refresh; refresh stored server-side  
4. Logout revokes refresh; optional access `jti` denylist in Redis  

---

## Failure Scenarios

| Failure | Behavior | Recovery |
|---------|----------|----------|
| **Redis down at ingest** | Trace still in Postgres; enqueue fails closed; analysis not started | Fix Redis; `POST .../reanalyze` |
| **Redis down for JWT denylist** | Deny/check **fail open** (availability); metric `raginspector_jwt_denylist_failopen_total` increments | Short access TTL + alert on fail-open; restore Redis |
| **Database down** | API readiness fails; writes error | Fail closed; restore Postgres from backup ([BACKUP.md](docs/BACKUP.md), [DISASTER_RECOVERY.md](docs/DISASTER_RECOVERY.md)) |
| **Worker crash mid-task** | `acks_late` → message redelivered; idempotent completion checks | Restart worker; scale replicas if backlog grows |
| **External LLM/HF API fails** | Optional judge path degrades; local NLI / heuristics remain | Unset tokens or fix provider; core grounding still local |
| **Network timeout (client)** | Client retries ingest carefully (idempotency depends on client design) | Prefer reanalyze by id over duplicate blind posts when unsure |
| **Auth failure** | 401 on missing/invalid token; 429 on login budget | Correct credentials; wait out rate limit |
| **Nginx / Docker Desktop publish flake (Windows)** | Host port resets while container `/live` still 200 | Probe in-network; use verify-ports overlay; see [WINDOWS.md](docs/WINDOWS.md) |

---

## Performance

Full tables and methodology: [docs/engineering/PERFORMANCE.md](docs/engineering/PERFORMANCE.md).

**Honest class of evidence:** laptop Docker Desktop, not a quiet prod rack.

| Signal | Ballpark |
|--------|----------|
| `/live` p50 | ~6 ms |
| Authenticated dashboard (cache hit) p50 | ~14–17 ms |
| Login (spaced) p50 | ~350–400 ms (bcrypt) |
| Ingest → analysis complete | ~10 s order-of-magnitude on seeded sample (queue + NLI) |
| Login rate limit | 20/minute — primary cause of “auth bench failures” |
| 30 min soak | ~0.1% probe errors; 0 restarts on recorded run |

**Bottlenecks:** model RAM per worker, dashboard aggregate SQL without cache, host Docker contention, intentional auth rate limits.

**Future:** quieter soak hosts, broader Playwright CI, exporter coverage when full obs stack is up, optional workflow engine only if queue complexity demands it.

---

## Security

| Area | Implementation |
|------|----------------|
| **Authentication** | JWT (PyJWT), refresh revoke in Postgres, optional access jti denylist in Redis, MFA TOTP with Fernet-encrypted secrets |
| **Authorization** | Org membership / roles, pipeline ACL, API key scopes, plan gates |
| **Secrets** | `.env` gitignored; `.env.example` completeness tested; prod `validate_production_settings()` |
| **Encryption** | TLS via Nginx overlay in docs; MFA secrets encrypted at rest; passwords bcrypt |
| **Validation** | Pydantic schemas; domain exceptions without stack traces to clients |
| **Rate limiting** | SlowAPI + Nginx zones |
| **Audit logging** | Audit endpoints/services for sensitive actions |
| **Supply chain** | Bandit, pip-audit, npm audit, Trivy, Gitleaks, SBOM scripts in CI |

Details: [SECURITY.md](SECURITY.md) · [docs/SECRETS.md](docs/SECRETS.md) · [docs/engineering/SECURITY.md](docs/engineering/SECURITY.md).

**Residual:** SAML/SCIM not GA; denylist fail-open without Redis; transitive npm moderate advisories may exist via Next — check current `npm audit`.

---

## Testing

| Layer | Location | Role |
|-------|----------|------|
| Backend unit | `backend/tests/unit/` | Services/workers; **critical coverage gate ≥95%** on configured packages |
| API | `backend/tests/test_api.py` | HTTP contracts |
| Integration | `backend/tests/integration/` | Redis/ready/etc. |
| SDK | `sdk/tests/` | Client behavior |
| Frontend | Vitest under `frontend/src` | Critical UI units |
| E2E | Playwright `frontend/e2e/` | Exists; historically flaky against Windows publish ports — not always CI-green |
| Load | `loadtests/` | k6 + Locust + Python harnesses |

CI: [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (lint, types, tests, security scans, Docker, Helm validate).  
Strategy doc: [docs/engineering/TESTING_STRATEGY.md](docs/engineering/TESTING_STRATEGY.md).

**Coverage honesty:** gates apply to critical modules, not every line of the monorepo.

---

## Deployment

| Mode | How |
|------|-----|
| **Local** | `.env` from example → `make bootstrap` → `make seed` |
| **Windows** | `scripts/setup.ps1` + verify-ports compose ([WINDOWS.md](docs/WINDOWS.md)) |
| **Docker Compose prod** | `docker-compose.prod.yml` — no bind mounts, limits, healthchecks ([COMPOSE_PROD.md](docs/COMPOSE_PROD.md)) |
| **Observability** | `make up-obs` — Prometheus/Grafana |
| **Kubernetes** | Helm chart `infrastructure/helm/raginspector` ([HELM.md](docs/HELM.md)) |
| **Health** | Liveness `/live`; readiness `/api/v1/ops/ready` (DB + Redis) |
| **Scaling** | More API replicas; more analysis workers at concurrency 1–2; HPA/KEDA templates optional |

Ops index: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) · [docs/RUNBOOKS.md](docs/RUNBOOKS.md) · [docs/SRE_CHECKLIST.md](docs/SRE_CHECKLIST.md).

---

## Real Enterprise Case Studies

Engineering-style narratives (fictionalized companies, realistic constraints). They illustrate how the product would be used — they are not customer testimonials claiming production deployments of this exact repo.

| Case | File | Theme |
|------|------|-------|
| Fintech cost | [01](docs/case-studies/01-fintech-hallucination-cost.md) | Dollarize hallucinations; hybrid retrieval |
| Healthcare retrieval | [02](docs/case-studies/02-healthcare-retrieval-quality.md) | Retrieval quality under clinical docs |
| SaaS regression | [03](docs/case-studies/03-saas-pre-deploy-regression.md) | Pre-deploy regression gates |
| Ecommerce gaps | [04](docs/case-studies/04-ecommerce-knowledge-gaps.md) | Knowledge gap loops |
| Enterprise SSO / obs | [05](docs/case-studies/05-enterprise-sso-observability.md) | Honesty about SSO + observability |
| Legal-tech vectors | [06](docs/case-studies/06-legaltech-vector-db-evaluation.md) | Vector DB evaluation with BM25 evidence |

---

## Lessons Learned

**Architecture**  
Offloading ML early was the right call. Keeping experimental IdP code without an honesty layer would have destroyed credibility faster than missing features.

**Trade-offs**  
Fat workers and some fat endpoints still exist; extracting `analysis_pipeline` / `ingest_service` improved testability but the modular monolith is not hexagonal purity.

**Unexpected challenges**  
- Prometheus scrape broken when metrics were JSON-encoded — fixed with plaintext content-type.  
- “Auth load broken” often meant **429**, not bad JWT code.  
- Windows Docker Desktop publish-port flakiness can make host probes fail while containers are healthy.

**Production lessons**  
Readiness must check DB + Redis. Workers must listen to both `analysis` and `celery` queues or beat/webhooks stall. Cold-start model load dominates first analysis after scale-up.

---

## What I Would Improve With Three More Months

Honest backlog — not a promise that the project is “done forever”:

1. **Stabilize Playwright against Compose** in CI (including Windows port documentation or Linux CI runners only).  
2. **Graduate SAML/SCIM only with real IdP integration tests** — or keep them experimental forever rather than fake GA.  
3. **Split analysis worker modules further**; shrink remaining SQL-in-route hotspots.  
4. **Quiet-host capacity study** with exporters up; publish environment-specific SLOs.  
5. **OSS polish:** issue/PR templates, README CI badges, short demo recording.  
6. **Optional:** stronger OpenTelemetry path if customers demand distributed traces across their RAG apps and this debugger.

---

## Frequently Asked Questions

### Is this a Langfuse competitor?

It overlaps in “observe LLM apps,” but the center of gravity is **RAG grounding and retrieval diagnostics**, self-hosted. It is not positioned as a full prompt playground SaaS.

### Is enterprise SSO done?

Google SSO can run with env credentials. SAML/SCIM are **not** GA. See [EXPERIMENTAL.md](docs/EXPERIMENTAL.md).

### Do I need a GPU?

No for the default local NLI path (CPU). GPU may help throughput but is not required for demos.

### Why does login fail after many rapid attempts?

Rate limit (`20/minute`). Wait and retry. Not an auth bug.

### Where is Trust Score computed?

Aggregate: `app/services/trust_scorer.py` (recent traces). Per-trace diagnostic fields come from the worker. Dashboard JSON often exposes `trustworthiness_score`.

### What happens if analysis never completes?

Check worker logs, Redis, queue depth (`/api/v1/ops/...` backlog metrics). Reanalyze the trace. Confirm workers consume `analysis`.

### Is billing required to use the product locally?

No. Razorpay needs live keys for real checkout; local free-tier path is the default demo.

---

## Interview Preparation

### Likely questions and strong answers

**Q: Walk me through a request from SDK to UI.**  
A: API key ingest → Postgres persist → Celery enqueue → worker grounding/BM25/failure/trust → dashboard query detail with sentence↔chunk UI. Ingest does not wait for NLI.

**Q: Why not analyze inline in FastAPI?**  
A: Multi-second RAM-heavy models; would wreck API p99 and couple web replicas to ML weights. ADR 0001.

**Q: How do you handle Redis outage?**  
A: Durability of traces in Postgres first; analysis deferred via reanalyze. JWT denylist fails open with metrics — short access TTL limits revoke window risk.

**Q: What’s the hardest bug you fixed in this repo?**  
A: Prefer real ones: metrics content-type breaking Prometheus `up`; CORS for verify-ports UI origin; login benches misread as outages when SlowAPI returned 429.

**Q: How do you avoid demoing fake enterprise features?**  
A: `docs/EXPERIMENTAL.md`, quarantined `/enterprise`, plan gates, and README honesty. Incomplete IdP is labeled incomplete.

**Q: How would you scale analysis?**  
A: Horizontal workers at concurrency 1–2, separate queues, backlog alerts, warm models on start — not thread explosion on one box.

**Q: What’s still weak?**  
A: Playwright flake on some hosts, IdP depth, whole-repo coverage mythology, Compose SPOF for Redis/Postgres unless you bring external managed services.

### Live demo script (≈2 minutes)

1. Seed login → dashboard Trust / cost cards.  
2. Open a hallucinated vs grounded query.  
3. Hover sentence grounding.  
4. Mention async worker + reanalyze.  
5. Explicitly say what is experimental.

Longer click-path: [docs/demo/DEMO_WALKTHROUGH.md](docs/demo/DEMO_WALKTHROUGH.md).

---

## Final Engineering Assessment

| Question | Answer |
|----------|--------|
| **What this repo demonstrates** | End-to-end RAG observability product thinking: SDK, async ML workers, grounding UX, auth, CI, Compose/Helm ops, and documentation discipline with an honesty layer |
| **Skills showcased** | Python API design, Celery/Redis ops, SQLAlchemy/Alembic, applied ML evaluation (NLI), Next.js, security basics, SRE-minded metrics, technical writing |
| **Roles it targets** | Applied AI / LLM platform / backend AI / founding engineer / senior full-stack with ML systems lean |
| **What interviewers should notice** | Real analysis path (not mocked end-to-end); ADRs with rejected alternatives; refusal to market SAML/SCIM as GA; performance evidence that admits hardware class and 429 behavior |

**Verdict for humans evaluating the tree:** Strong self-hosted RAG debugger and portfolio/OSS project. Conditional for production self-host (ops docs + Compose proven path). Not a turnkey IdP-complete enterprise SaaS.

---

## Document map (where to go next)

| Need | Document |
|------|----------|
| Clone and run | [README.md](README.md) |
| Binding architecture | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| Decisions | [docs/adr/](docs/adr/) |
| What’s shipped vs experimental | [docs/IMPLEMENTED.md](docs/IMPLEMENTED.md), [docs/EXPERIMENTAL.md](docs/EXPERIMENTAL.md) |
| Performance numbers | [docs/engineering/PERFORMANCE.md](docs/engineering/PERFORMANCE.md) |
| Ops / DR | [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md), [docs/RUNBOOKS.md](docs/RUNBOOKS.md) |
| Cleanup history | [docs/REMOVED.md](docs/REMOVED.md) |
| Roadmap contract | [ROADMAP.md](ROADMAP.md) |
