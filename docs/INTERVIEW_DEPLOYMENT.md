# Interview Deployment Report — RAGInspector

**Verified:** 2026-07-19  
**Verdict:** **Interview Deployment Ready** (with host RAM caveats below)

This document is the single source of truth for cloning, configuring, starting, demonstrating, and manually validating the product with **minimum external dependencies**. It does **not** describe a commercial SaaS launch.

For **Vercel + Render** portfolio hosting, see [`DEPLOYMENT.md`](DEPLOYMENT.md).

---

## Quick start (interview path)

### Prerequisites

| Requirement | Notes |
|-------------|--------|
| Docker Desktop + Compose v2 | Required |
| ~8 GB host RAM free for the stack | Live Celery NLI needs headroom; stop other Docker projects |
| Outbound HTTPS | First ML model download from Hugging Face (cached in volume) |
| Optional: HF token / Ollama | Not required for seeded demo UI |

### Commands used in this validation (Windows + busy ports)

```powershell
# From repo root
Copy-Item .env.example .env   # if missing; set SECRET_KEY (>= 32 chars)

# Start core stack + interview worker tuning + port remaps
docker compose `
  -f docker-compose.yml `
  -f docker-compose.verify-ports.yml `
  -f docker-compose.interview.yml `
  up -d --build

# Migrations
docker compose `
  -f docker-compose.yml `
  -f docker-compose.verify-ports.yml `
  -f docker-compose.interview.yml `
  run --rm backend alembic upgrade head

# Demo user + pre-analyzed traces (no live ML required for UI walkthrough)
docker compose `
  -f docker-compose.yml `
  -f docker-compose.verify-ports.yml `
  -f docker-compose.interview.yml `
  run --rm backend python scripts/seed_demo.py
```

### Optional observability

```powershell
docker compose `
  -f docker-compose.yml `
  -f docker-compose.verify-ports.yml `
  -f docker-compose.interview.yml `
  -f docker-compose.observability.yml `
  up -d
```

### Surfaces (verify-ports overlay)

| Surface | URL |
|---------|-----|
| UI | http://127.0.0.1:13000 |
| API | http://127.0.0.1:18000 |
| Nginx | http://127.0.0.1:18080 |
| OpenAPI / Swagger | http://127.0.0.1:18000/docs |
| Prometheus (if obs overlay) | http://127.0.0.1:19090 |
| Grafana (if obs overlay) | http://127.0.0.1:13001 (admin / admin) |

**Demo login:** `demo@example.com` / `DemoPass123!`

### Linux / macOS (default ports free)

```bash
cp .env.example .env   # set SECRET_KEY
docker compose -f docker-compose.yml -f docker-compose.interview.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.interview.yml run --rm backend alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.interview.yml run --rm backend python scripts/seed_demo.py
# UI http://localhost:3000  API http://localhost:8000
```

Or: `make bootstrap` then `make seed` (POSIX Make; on Windows prefer `.\scripts\bootstrap.ps1`).

---

## Phase 1 — Deployment audit & dependency graph

### Required services (interview core)

| Service | Role |
|---------|------|
| **db** (Postgres 16 + pgvector) | Primary datastore |
| **redis** | Celery broker/backend, JWT denylist, dashboard cache |
| **backend** (FastAPI) | REST API, auth, ingest, metrics |
| **celery_worker** | Async analysis (NLI, BM25, Trust Score) |
| **celery_beat** | Scheduled jobs (probes, reports, citation rates) |
| **frontend** (Next.js) | Dashboard |
| **nginx** | Reverse proxy |

### Optional services

| Service | Role | Interview? |
|---------|------|------------|
| postgres_backup | Daily `pg_dump` | Nice-to-have |
| prometheus / grafana / exporters | Observability overlay | Optional demo |
| Helm / K8s / Terraform | Cluster deploy | Out of interview scope |

### External APIs

| API | Required? |
|-----|-----------|
| Hugging Face Inference (`HF_API_TOKEN`) | No — optional LLM judge |
| Ollama | No — optional fallback |
| Hugging Face Hub (model download) | First analysis only (local cache thereafter) |
| Razorpay / Resend / SMTP / Google OAuth / Sentry / OTel | No |

### Not in the live product

OpenAI, Groq, Gemini, Anthropic, MinIO/S3, Stripe — appear only in archived PRD docs.

### Dependency graph

```text
  Browser / SDK
        │
        ▼
     Nginx ──► Next.js UI
        │
        ▼
     FastAPI ──► PostgreSQL (+ pgvector)
        │
        ├──► Redis ◄── Celery worker (analysis queue)
        │                  │
        │                  ▼
        └──► Celery beat   Local NLI + embeddings
                           (HF cache; optional HF/Ollama LLM)
```

**Object storage:** none — documents/chunks live in Postgres.  
**Queues:** Celery over Redis (`analysis`, `celery`).

---

## Phase 2 — Required secrets inventory

| Variable | Required? | Purpose | Example | Blank OK? | Mockable? | Interview safe default |
|----------|-----------|---------|---------|-----------|-----------|------------------------|
| `SECRET_KEY` | **Yes** | JWT + Fernet-derived MFA crypto | `python -c "import secrets; print(secrets.token_urlsafe(32))"` | No | No | Any ≥32-char random string |
| `POSTGRES_PASSWORD` | Yes (compose) | DB auth | `raginspector_secret` | No for compose | N/A | Dev default OK locally |
| `REDIS_PASSWORD` | Yes (compose) | Redis auth | `redis_secret` | No for compose | N/A | Dev default OK locally |
| `DATABASE_URL` / `DATABASE_SYNC_URL` | Auto in compose | ORM / Alembic / Celery | compose constructs `@db:5432` | Yes if compose sets them | N/A | Leave to compose |
| `REDIS_URL` | Auto in compose | Broker + denylist | `redis://:redis_secret@redis:6379/0` | Yes if compose sets it | N/A | Leave to compose |
| `FRONTEND_URL` | Recommended | CORS / email links | `http://127.0.0.1:13000` | Soft | N/A | Match UI origin |
| `NEXT_PUBLIC_API_URL` | Recommended | Browser → API | `http://127.0.0.1:18000` | Soft | N/A | Match API (verify-ports sets this) |
| `ALLOWED_HOSTS` | Recommended | Host header allowlist | `localhost,127.0.0.1` | Soft | N/A | Localhost list |
| `ENVIRONMENT` | Soft | Feature gates / docs | `development` | Yes | N/A | `development` |
| `REQUIRE_EMAIL_VERIFICATION` | Soft | Login gate | `false` | Yes | N/A | `false` for interview |
| `HF_API_TOKEN` | **No** | Optional LLM metrics | blank | **Yes** | Yes (skip) | **Leave blank** |
| `OLLAMA_*` | **No** | Optional local LLM | defaults | Yes | Yes | Leave defaults; unused if no Ollama |
| `EMBEDDING_MODEL_NAME` / `NLI_MODEL_NAME` | Soft | Local ML ids | repo defaults | Yes | N/A | Defaults |
| `WARM_ML_MODELS_ON_WORKER_START` | Soft | Preload models | `false` on low RAM | Yes | N/A | `false` via interview overlay |
| `RAZORPAY_*` / `NEXT_PUBLIC_RAZORPAY_*` | **No** | Billing checkout | blank | **Yes** | Partial (usage API still works) | Blank |
| `RESEND_*` / `SMTP_*` | **No** | Email | blank | **Yes** | Yes | Blank |
| `GOOGLE_OAUTH_*` | **No** | SSO | blank | **Yes** | Yes | Blank |
| `SENTRY_DSN` / `OTEL_*` | **No** | APM | blank | **Yes** | Yes | Blank |
| `OPS_SHARED_TOKEN` | **No** (dev) | Gate ops backlog | blank | Yes | N/A | Blank in dev |
| `SUPPORT_ADMIN_EMAILS` | **No** | Support admin | blank | Yes | N/A | Blank |
| Plan quota overrides | **No** | Trace limits | defaults | Yes | N/A | Defaults |

**Why each family exists**

- **SECRET_KEY** — signs JWTs; without a stable secret, sessions break across restarts.
- **Postgres / Redis** — hard dependencies for `/ops/ready` and workers.
- **HF / Ollama** — optional answer-quality LLM path; grounding uses local NLI.
- **Razorpay / email / OAuth / Sentry** — SaaS integrations; product runs without them.

Never require commercial cloud, payment, or SSO accounts for an interview demo.

---

## Phase 3 — Minimal interview configuration

| Choice | Decision |
|--------|----------|
| Database | **PostgreSQL** (SQLite is local-dev fallback only; Compose uses Postgres) |
| Cache / broker | **Redis** (required) |
| Object storage | **None** |
| ML | Local sentence-transformers; `docker-compose.interview.yml` → concurrency=1, `WARM_ML_MODELS_ON_WORKER_START=false` |
| LLM judge | Disabled (blank `HF_API_TOKEN`, no Ollama) |
| Billing / SSO / email / Sentry | Disabled |
| Observability | Optional overlay |
| Auth for demo | Seeded JWT user + API keys |

Files:

- `.env` from `.env.example` (set `SECRET_KEY` only for a clean interview clone)
- `docker-compose.interview.yml` (low-RAM worker)
- `docker-compose.verify-ports.yml` on Windows when ports collide

---

## Phase 4 — Deployment verification (executed)

| Check | Result |
|-------|--------|
| Docker build / compose up | Pass |
| `GET /live`, `/health` | 200 |
| `GET /api/v1/ops/ready` | `database=ok`, `redis=ok`, migrations `020_*` |
| Frontend | 200 on `:13000` |
| Nginx | 200 on `:18080` |
| OpenAPI `/docs` | 200 |
| Prometheus metrics `/api/v1/ops/metrics` | 200 |
| Alembic | At head (`020_trace_observability_fields`) |
| Celery worker / beat | Up; worker may report **unhealthy** during long ML (inspect ping timeout) while still processing |
| Seed | `demo@example.com` present |
| Auth login | Pass |
| Observability (Prometheus/Grafana) | Pass when overlay running |

### Compose files involved

```text
docker-compose.yml
docker-compose.verify-ports.yml      # Windows port remap
docker-compose.interview.yml         # concurrency=1, warm=false
docker-compose.observability.yml     # optional
```

---

## Phase 5 — Manual test plan

Use verify-ports URLs unless noted. Login: `demo@example.com` / `DemoPass123!`.

### Checklist (start → finish)

- [ ] Stack healthy: `curl http://127.0.0.1:18000/api/v1/ops/ready`
- [ ] Open UI; login with demo credentials
- [ ] Dashboard shows seeded metrics (`total_queries` ≥ 4)
- [ ] Queries list → open a completed trace → see grounding sentences
- [ ] Chunks page shows citation stats
- [ ] Autofix recommendations list non-empty (seed)
- [ ] Settings page loads
- [ ] Billing usage shows plan (seed: starter) — no Razorpay keys needed
- [ ] Create API key in UI or `POST /api/v1/keys`
- [ ] Ingest a trace (below) → wait for `analysis_status=completed`
- [ ] Re-open query detail → Trust Score / failure type populated
- [ ] API docs: `/docs` try-it-out with Bearer token
- [ ] (Optional) Grafana dashboards under observability overlay

### Feature matrix

| Feature | Prerequisites | Steps | Expected | Failure indicators | Logs / API |
|---------|---------------|-------|----------|--------------------|------------|
| Login | Seeded user | UI login or `POST /api/v1/auth/login` | Tokens returned | 401 Invalid email or password | backend logs |
| Register | None | `POST /api/v1/auth/register` `{email,password,name}` | 201 user | 422 validation | — |
| Pipelines | JWT | `GET /api/v1/pipelines` | Includes Demo Support Bot | 401 | — |
| Dashboard | JWT | UI Dashboard / `GET /api/v1/metrics/dashboard` | Aggregates | Empty if no traces | — |
| Query detail / grounding | Seeded or analyzed trace | UI `/queries/{id}` | Grounding rows, scores | `analysis_status` stuck | `docker logs raginspector_worker` |
| API key + ingest | JWT | Create key → `POST /api/v1/ingest/trace` with `X-API-Key` | 202 + `trace_id` | 401 bad key; 422 schema | — |
| Autofix | Seed | UI Autofix / `GET /api/v1/autofix/recommendations` | Items | Empty without seed | — |
| Documents | JWT | `GET /api/v1/documents` | 200 (may be empty) | 401 | — |
| Monitoring / Benchmark | **Pro plan** | `GET .../monitoring/config/{id}` | 403 on starter seed | Expected on demo plan | Plan gate |
| Regression snapshots | JWT | `GET /api/v1/regression/snapshots/{pipeline_id}` | 200 list (may be `[]`) | 401 | — |
| Ops metrics | None | `GET /api/v1/ops/metrics` | Prometheus text | — | — |

### Example: login

```http
POST /api/v1/auth/login
Content-Type: application/json

{"email":"demo@example.com","password":"DemoPass123!"}
```

Expected: `access_token`, `refresh_token`, `mfa_required: false`.

### Example: ingest (schema from OpenAPI)

```http
POST /api/v1/ingest/trace
X-API-Key: ri-...
Content-Type: application/json

{
  "pipeline_name": "Demo Support Bot",
  "query_text": "What is the refund policy for annual plans?",
  "answer_text": "Annual plans can be refunded within 14 days of purchase with a full refund.",
  "retrieved_chunks": [
    {
      "chunk_id": "billing-refund-1",
      "chunk_text": "Refunds for annual subscriptions are available within 14 days of purchase.",
      "similarity_score": 0.91,
      "rank": 1
    }
  ]
}
```

Expected: `202` with `trace_id`. Then poll `GET /api/v1/queries/{trace_id}` until `analysis_status=completed`.

**DB changes:** rows in `query_traces`, `retrieved_chunks`, `grounding_results`, `analysis_jobs`.

---

## Phase 6 — End-to-end validation results

| Workflow | Result | Evidence |
|----------|--------|----------|
| Seed / login | Pass | JWT issued for demo user |
| Pipelines / queries / dashboard / chunks / autofix / billing / settings | Pass | HTTP 200 |
| Register new user | Pass | HTTP 201 |
| Create API key | Pass | HTTP 201 + `raw_key` |
| Ingest trace | Pass | HTTP 202, stored even if worker busy |
| Live Celery analysis | Pass | Trace `65a3bfea-…` → `completed`, `failure_type=retrieval_irrelevant`, `trustworthiness_score=47.2`, `is_hallucination=true`, grounding_results=1 (~390s on constrained host) |
| Seeded grounding UI path | Pass | Pre-analyzed seed: trust≈90.9, grounded=1 |
| Persistence after backend restart | Pass | `total_queries` 6 → 6 |
| Prometheus / Grafana | Pass | Ready/health 200 |
| Pro-gated monitoring/benchmark | Expected 403 on starter | Plan gate working |

---

## Phase 7 — Failure testing results

| Scenario | Result | Observed |
|----------|--------|----------|
| Invalid login | Pass | `401` `Invalid email or password` |
| Missing JWT | Pass | `401` `Could not validate credentials` |
| Bad JWT | Pass | `401` |
| Bad API key | Pass | `401` `Invalid or revoked API key` |
| Invalid register body | Pass | `422` |
| Worker unavailable at ingest | Pass | Trace stored; message to `reanalyze` later |
| Redis stopped | Pass | Readiness fails / API stress; recovers after `docker start raginspector_redis` |
| Missing HF / Ollama | Pass | Analysis completes; Ollama failure logged; local NLI still runs |
| Unauthorized pro features | Pass | `403` plan upgrade required |
| Low host RAM / worker OOM | Observed | Prefork warm + concurrency=2 caused SIGKILL; mitigated by interview overlay |

**Graceful degradation:** ingest persists traces without Celery; JWT denylist fails open without Redis (short TTL); LLM optional.

---

## Phase 8 — Optional integrations

| Integration | Enables | Interview required? | Disable | Mock |
|-------------|---------|---------------------|---------|------|
| Hugging Face Inference | Optional LLM judge metrics | No | Blank `HF_API_TOKEN` | Leave blank |
| Ollama | Local LLM fallback | No | Don’t run Ollama | Leave blank URL |
| Local NLI / embeddings | Core grounding quality | Needed for **live** analysis | N/A | Seed bypasses need |
| Razorpay | Checkout / webhooks | No | Blank keys | Usage endpoint still works |
| Resend / SMTP | Verification & reset email | No | Blank | `REQUIRE_EMAIL_VERIFICATION=false` |
| Google OAuth | SSO | No | Blank `GOOGLE_OAUTH_*` | Password login |
| Sentry / OTel | APM | No | Blank | structlog only |
| Prometheus/Grafana | Ops demo | Optional | Omit obs compose | `/ops/metrics` still on API |
| Slack webhook (per user) | Alert delivery | No | Don’t set in settings | — |
| SAML / SCIM | Enterprise IdP | No | Unused stubs | See EXPERIMENTAL.md |

---

## Phase 9 — Interview demo script (10–15 min)

### 0:00–1:30 — System overview

- Problem: RAG fails without separating retrieval misses from hallucinations.
- Stack: Next.js → Nginx → FastAPI → Postgres + Celery/Redis + local NLI.
- Honesty: SSO/billing partial; core debugger path is live ([EXPERIMENTAL.md](EXPERIMENTAL.md)).

### 1:30–3:00 — Startup & architecture

- Show `docker compose ps` (healthy db/redis/backend/frontend).
- Show `/api/v1/ops/ready` JSON (DB, Redis, migrations, backlog).
- Draw request path: SDK ingest → persist → queue → worker → dashboard.

### 3:00–7:00 — Feature walkthrough (seed)

1. Login as demo user.
2. Dashboard: hallucination rate, faithfulness, Trust Score aggregates.
3. Queries: open grounded vs hallucination seed traces.
4. Point at sentence↔chunk grounding UI.
5. Chunks / Autofix: citation heatmap + recommendation.

### 7:00–10:00 — Live path (if RAM allows)

1. Create API key.
2. Ingest sample trace (schema above).
3. Watch worker logs; poll until completed.
4. Explain failure class + Trust Score.

If RAM is tight: stay on seed and explain that seed is intentional for demos ([SEED.md](SEED.md)).

### 10:00–12:00 — Engineering decisions

- Async ML off the request path (Celery + time limits).
- Local NLI vs paid LLM judges.
- Plan gates for pro features.
- Fail-closed production settings vs interview `development`.

### 12:00–14:00 — Monitoring

- `/api/v1/ops/metrics` scrape.
- Optional Grafana.
- Worker backlog soft checks on ready.

### 14:00–15:00 — Limitations & Q&A

- Host RAM for ML; first model download latency.
- Pro features need plan upgrade on seed user.
- Google SSO / Razorpay need real credentials.
- Worker healthcheck can flap during long analysis.

### Likely interviewer questions

| Question | Answer cue |
|----------|------------|
| Why Celery not inline? | NLI can take tens of seconds–minutes; keep API latency low |
| Why Postgres not SQLite in compose? | Concurrent workers, pgvector, production parity |
| What if Redis dies? | Ready fails; ingest/analysis degrade; denylist fail-open |
| How do you prevent hallucination false positives? | Sentence-level NLI + BM25 comparison + Trust Score blend |
| What’s incomplete? | SSO/billing/SCIM — see EXPERIMENTAL.md |

---

## Phase 10 — Deployment report summary

### Deployment Status

**Interview Deployment Ready** — core stack starts, seed demo is fully walkable, live ingest→analysis verified, secrets documented, optional integrations identified. Live ML needs adequate free RAM (stop competing containers).

### Services Started

`db`, `redis`, `backend`, `celery_worker`, `celery_beat`, `postgres_backup`, `frontend`, `nginx` (+ optional `prometheus`, `grafana`)

### Required Secrets

`SECRET_KEY`, compose Postgres/Redis passwords (dev defaults acceptable for local interview only)

### Optional Secrets

`HF_API_TOKEN`, Razorpay, email, Google OAuth, Sentry, OTel, `OPS_SHARED_TOKEN`

### Required Infrastructure

Docker, Postgres, Redis, Celery worker+beat, FastAPI, Next.js

### Optional Infrastructure

Observability stack, TLS overlay, Helm/K8s, Ollama, HF Inference

### Manual Test Checklist

See Phase 5.

### End-to-End Validation Results

See Phase 6 — pass, including live analysis completion and restart persistence.

### Known Limitations

1. **Host RAM:** ~8 GB free recommended; competing Docker stacks cause worker OOM / multi-minute analysis.
2. **Worker healthcheck** may show `unhealthy` during long ML while tasks still succeed.
3. **Demo plan is starter** — monitoring/benchmark/studio/investigator return 403 until plan upgrade.
4. **HF/Ollama optional** — LLM metric enrichment may be skipped; grounding still runs.
5. **Google OAuth env** documented but not all vars are passed in every compose block — set via `.env` + compose env if demoing SSO.
6. **PRD archive** may mention OpenAI/Groq/MinIO — not the shipped stack.

### Troubleshooting Guide

| Symptom | Fix |
|---------|-----|
| Port bind errors on Windows | Add `docker-compose.verify-ports.yml` |
| Worker SIGKILL / restart loop | Use `docker-compose.interview.yml`; free RAM; set `WARM_ML_MODELS_ON_WORKER_START=false` |
| Ingest says worker unavailable | `docker compose … up -d celery_worker` then `POST …/reanalyze` |
| Empty UI metrics | Run `seed_demo.py` |
| CORS / blank API calls from UI | Align `FRONTEND_URL` and `NEXT_PUBLIC_API_URL` with actual ports |
| First analysis very slow | Expected: model download/load; subsequent traces faster |
| Ready fails redis/db | `docker compose ps`; check passwords match `.env` |
| 403 on monitoring | Expected on starter; upgrade plan in DB/admin or demo with seed features only |

### Interview Readiness Assessment

| Criterion | Met? |
|-----------|------|
| Starts successfully | Yes |
| Core features functional | Yes (seed + verified live analysis) |
| Manual testing passes | Yes |
| Documentation matches reality | Yes (this file + README) |
| Required secrets documented | Yes |
| Optional integrations identified | Yes |
| Demo without commercial SaaS accounts | Yes |

**Mark: Interview Deployment Ready.**

---

## Related docs

- [SEED.md](SEED.md) — demo dataset  
- [WORKER.md](WORKER.md) / [COLD_START.md](COLD_START.md) — Celery & ML RAM  
- [WINDOWS.md](WINDOWS.md) — port overlays  
- [EXPERIMENTAL.md](EXPERIMENTAL.md) / [IMPLEMENTED.md](IMPLEMENTED.md) — honesty inventory  
- [API.md](API.md) — endpoint reference  
- [../PROJECT_GUIDE.md](../PROJECT_GUIDE.md) — engineering deep dive  
