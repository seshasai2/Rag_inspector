# API Keys & Environment Variables Guide

**Mode:** Interview / portfolio demonstration  
**Verified from:** `backend/app/core/config.py`, compose files, frontend env usage, and service call sites  
**Date:** 2026-07-20

This guide answers: what must be set, what can stay blank, and what still works without commercial SaaS accounts.

**Not in this codebase:** `OPENAI_API_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `ANTHROPIC_*`, `MINIO_*`, `STRIPE_*`, `DODO_*` — they do not appear in application code (PRD archive docs may mention some historically).

---

## Overview

| Category | Count (approx.) |
|----------|-----------------|
| Variables in `Settings` (`config.py`) | 50 |
| Compose / deploy-only (not in Settings) | ~15 |
| Frontend `NEXT_PUBLIC_*` | 2 |
| Test / CI-only | ~5 |
| **Absolutely required commercial API keys** | **0** |
| **Infrastructure services for Compose interview** | Postgres + Redis (via Docker) |

Core demo path (seed → login → dashboard → grounding UI) needs **no** Hugging Face, Ollama, Razorpay, email, or OAuth keys.

---

## Required Environment Variables

### Interview / local Docker Compose

| Variable | Required? | Purpose | Default | Can Be Empty? | Used By |
|----------|-----------|---------|---------|---------------|---------|
| `SECRET_KEY` | **Recommended** (dev has weak default) | JWT sign/verify + MFA Fernet key material | `supersecretkey_change_in_production_min_32_chars` | No (has default) | `app.core.security`, MFA |
| `DATABASE_URL` | Yes (Compose sets it) | Async SQLAlchemy | localhost Postgres URL | No for real demos | `db/session.py`, API |
| `DATABASE_SYNC_URL` | Yes (Compose sets it) | Alembic + Celery sync DB | localhost Postgres URL | No | `migrations/env.py`, workers |
| `REDIS_URL` | Yes (Compose sets it) | Celery broker, JWT denylist, cache, `/ops/ready` | `redis://:redis_secret@localhost:6379/0` | No for Compose | Celery, redis clients, ops |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | Compose-only | Postgres container bootstrap | `raginspector` / `raginspector_secret` / `raginspector` | No in Compose | `docker-compose.yml` |
| `REDIS_PASSWORD` | Compose-only | Redis `--requirepass` | `redis_secret` | No in Compose | `docker-compose.yml` |
| `FRONTEND_URL` | Soft | CORS + email links | `http://localhost:3000` | Soft | `main.py`, auth, identity |
| `NEXT_PUBLIC_API_URL` | Soft (defaults) | Browser → API base URL | `http://localhost:8000` | Soft locally | `frontend/src/lib/api.ts`, `next.config.js` |
| `ALLOWED_HOSTS` | Soft in dev | TrustedHost in production | `localhost,127.0.0.1` | Soft in dev | `main.py` |
| `ENVIRONMENT` | Soft | Feature gates / docs / validation | `development` | Soft | Throughout |
| `REQUIRE_EMAIL_VERIFICATION` | Soft | Hard-gate login until verified | `false` in unset+dev; **true** if prod+unset | Soft | `auth.py` |

For a clean clone: copy `.env.example` → `.env`, set a strong `SECRET_KEY`, run Compose. DB/Redis URLs are injected by Compose.

### Production / free cloud (`ENVIRONMENT=production`)

`validate_production_settings()` **fails closed** unless:

| Variable | Notes |
|----------|--------|
| `SECRET_KEY` | ≥32 chars, not the built-in default |
| `DATABASE_URL` / `DATABASE_SYNC_URL` | Non-localhost, not `raginspector_secret` |
| `REDIS_URL` | Non-localhost, not `redis_secret` |
| `FRONTEND_URL` | Must be `https://…` |
| `ALLOWED_HOSTS` | No `localhost` / `127.0.0.1` |
| `OPS_SHARED_TOKEN` | ≥16 chars |
| `REQUIRE_EMAIL_VERIFICATION` | Set `false` for demos without mail, else configure Resend/SMTP |
| `NEXT_PUBLIC_API_URL` | Vercel build-time HTTPS API URL |

---

## Optional Environment Variables

### API keys & third-party credentials

| Variable | Importance | Purpose | Default | Can Be Empty? | Used By |
|----------|------------|---------|---------|---------------|---------|
| `HF_API_TOKEN` | OPTIONAL | Hugging Face Inference API for some LLM metrics / judge paths | `None` | **Yes** | `analysis_pipeline.py`, `ragas_service.py`, investigator (token checked but HF path mostly skipped) |
| `HF_MODEL` | OPTIONAL | HF model id when token set | `HuggingFaceH4/zephyr-7b-beta` | Soft | Analysis / RAGAS |
| `OLLAMA_BASE_URL` | OPTIONAL | Local Ollama HTTP API | `http://localhost:11434` | Soft | Analysis + investigator fallback |
| `OLLAMA_MODEL` | OPTIONAL | Ollama model name | `llama3.2:3b` | Soft | Same |
| `RAZORPAY_KEY_ID` | OPTIONAL | Razorpay checkout client | `None` | **Yes** | `billing.py` |
| `RAZORPAY_KEY_SECRET` | OPTIONAL | Razorpay server auth | `None` | **Yes** | `billing.py` |
| `RAZORPAY_WEBHOOK_SECRET` | OPTIONAL | Webhook HMAC verify | `None` | **Yes** | `billing.py` |
| `NEXT_PUBLIC_RAZORPAY_KEY_ID` | OPTIONAL | Frontend checkout key | `''` | **Yes** | `next.config.js` |
| `RAZORPAY_PLAN_*` (6 vars) | OPTIONAL | Map Razorpay plan IDs → tiers | `None` | **Yes** | `billing.py` |
| `RESEND_API_KEY` | OPTIONAL | Transactional email (primary) | `None` | **Yes** | `email_service.py` |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASSWORD` | OPTIONAL | SMTP fallback email | `None` | **Yes** | `email_service.py` |
| `SMTP_PORT` | OPTIONAL | SMTP port | `587` | Soft | `email_service.py` |
| `SMTP_FROM` | OPTIONAL | From address | `noreply@raginspector.com` | Soft | `email_service.py` |
| `GOOGLE_OAUTH_CLIENT_ID` | OPTIONAL | Google SSO | `None` | **Yes** | `identity.py` (all three required together) |
| `GOOGLE_OAUTH_CLIENT_SECRET` | OPTIONAL | Google SSO | `None` | **Yes** | `identity.py` |
| `GOOGLE_OAUTH_REDIRECT_URI` | OPTIONAL | OAuth callback URL | `None` | **Yes** | `identity.py` |
| `SENTRY_DSN` | OPTIONAL | Error tracking | `None` | **Yes** | `sentry_init.py` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | OPTIONAL | OpenTelemetry export | unset | **Yes** | `otel.py` (`os.environ`, not Settings) |
| `SUPPORT_ADMIN_EMAILS` | OPTIONAL | Comma-separated support admin allowlist | `""` | **Yes** | `admin.py` |
| `OPS_SHARED_TOKEN` | OPTIONAL in **dev**; **REQUIRED in production** | Gate `/ops/backlog` (+ related) via `X-Ops-Token` | `None` | Yes in development | `ops.py` |

### ML / analysis tuning (not SaaS keys)

| Variable | Importance | Purpose | Default | Can Be Empty? | Used By |
|----------|------------|---------|---------|---------------|---------|
| `EMBEDDING_MODEL_NAME` | RECOMMENDED for live analysis | Local sentence-transformers id | `all-MiniLM-L6-v2` | Soft | `ml_models.py` |
| `NLI_MODEL_NAME` | RECOMMENDED for live analysis | Local NLI cross-encoder | `cross-encoder/nli-deberta-v3-small` | Soft | `ml_models.py` |
| `WARM_ML_MODELS_ON_WORKER_START` | RECOMMENDED | Preload models on Celery fork | `true` | Soft | `celery_app.py` — use `false` on low RAM |
| `ANALYSIS_SOFT_TIME_LIMIT_SECONDS` | OPTIONAL | Celery soft limit | `600` | Soft | `tasks.py` |
| `ANALYSIS_HARD_TIME_LIMIT_SECONDS` | OPTIONAL | Celery hard limit | `720` | Soft | `tasks.py` |
| `HYBRID_VECTOR_WEIGHT` | OPTIONAL | BM25/hybrid merge | `0.5` | Soft | `analysis_pipeline.py` |
| `HYBRID_BM25_WEIGHT` | OPTIONAL | BM25/hybrid merge | `0.5` | Soft | `analysis_pipeline.py` |

### Auth / app behavior

| Variable | Importance | Purpose | Default | Can Be Empty? | Used By |
|----------|------------|---------|---------|---------------|---------|
| `ALGORITHM` | Soft | JWT algorithm | `HS256` | Soft | `security.py` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Soft | Access JWT TTL | `15` | Soft | `security.py` |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Soft | Refresh JWT TTL | `7` | Soft | `security.py`, auth |
| `DASHBOARD_METRICS_CACHE_ENABLED` | OPTIONAL | Redis dashboard cache | `True` | Soft | `dashboard_cache.py` |
| `DASHBOARD_METRICS_CACHE_TTL_SECONDS` | OPTIONAL | Cache TTL | `30` | Soft | `dashboard_cache.py` |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | Soft | Redis connect timeout | `0.5` | Soft | Redis clients / ops |
| `REDIS_SOCKET_TIMEOUT` | Soft | Redis op timeout | `0.5` | Soft | Same |
| `LOG_LEVEL` | Soft | Log verbosity | `INFO` | Soft | `logging.py` |
| `LOG_RETENTION_DAYS` | **Defined but unused in app code** | Intended log retention | `30` | Soft | **Only in `Settings`** — no runtime reader found |
| `FREE_TRACES_PER_MONTH` etc. | OPTIONAL | Plan quota overrides | 100 / 10k / 100k / … | Soft | `ingest_service.py`, billing |

### Deploy / runtime (not always in Settings)

| Variable | Importance | Purpose | Default | Used By |
|----------|------------|---------|---------|---------|
| `PORT` | Cloud REQUIRED | HTTP listen port | `8000` via script | `scripts/start_api.sh` |
| `UVICORN_WORKERS` | Soft | Uvicorn worker count | `1` (script) / `2` (Compose) | `start_api.sh`, compose |
| `RUN_MIGRATIONS` | Soft | `alembic upgrade head` on start | `0` | `docker-entrypoint.sh` |
| `CELERY_CONCURRENCY` / `CELERY_QUEUES` / `CELERY_LOGLEVEL` | Soft | Worker process | `1` / `analysis,celery` / `info` | `start_worker.sh` |
| `BACKUP_RETENTION_DAYS` | OPTIONAL | Backup sidecar cleanup | `14` | Compose backup service |
| `HTTP_PORT` / `HTTPS_PORT` / `TLS_CERTS_DIR` | Prod Compose / TLS | Published ports / certs | `80` / `443` | prod compose overlays |
| `GRAFANA_ADMIN_USER` / `GRAFANA_ADMIN_PASSWORD` | Observability overlay | Grafana login | `admin` / `admin` | `docker-compose.observability.yml` |

### Development / test only

| Variable | Purpose | Used By |
|----------|---------|---------|
| `TESTING` | Disables rate limits when truthy | `rate_limit.py`, CI |
| `TEST_DATABASE_URL` | Override DB for API/integration tests | `tests/test_api.py`, integration conftest |
| `FORCE_POSTGRES` | Forbid SQLite fallback | `db/session.py`, CI |
| `CI` | Playwright CI behavior | `playwright.config.ts` |
| `DEMO_EMAIL` / `DEMO_PASSWORD` | E2E credentials | Playwright tests |
| `API_BASE_URL` / `RAGINSPECTOR_API_URL` / `PLAYWRIGHT_*` / `RAGINSPECTOR_UI_URL` | E2E URLs | Playwright |

---

## Classification summary

### REQUIRED (cannot run meaningful demo without)

- **PostgreSQL** (Compose service or managed) via `DATABASE_URL` / `DATABASE_SYNC_URL`
- **Redis** via `REDIS_URL` (hard check on `/api/v1/ops/ready`; Celery; prod validation)
- **`SECRET_KEY`** (JWT) — weak default exists in development only

### RECOMMENDED

- Strong custom `SECRET_KEY` even in interviews
- `REQUIRE_EMAIL_VERIFICATION=false` for demos without mail
- Matching `FRONTEND_URL` + `NEXT_PUBLIC_API_URL` for UI
- Seed script (`seed_demo.py`) so UI works without live ML worker RAM

### OPTIONAL

- `HF_API_TOKEN`, Ollama, Razorpay, Resend/SMTP, Google OAuth, Sentry, OTel, Grafana passwords, plan quota overrides

### DEVELOPMENT ONLY

- `TESTING`, `TEST_DATABASE_URL`, `FORCE_POSTGRES`, Playwright/`DEMO_*` vars, Compose verify-ports remaps

### PRODUCTION ONLY (extra vs local)

- Strong `SECRET_KEY`, HTTPS `FRONTEND_URL`, non-localhost hosts/DB/Redis, `OPS_SHARED_TOKEN`, typically `REQUIRE_EMAIL_VERIFICATION=true` + mail provider

---

## Feature impact (API keys & providers)

### `HF_API_TOKEN` / `HF_MODEL`

- **Feature:** Optional LLM-assisted metrics (RAGAS-style paths) when analysis runs.
- **If missing:** Local NLI/embeddings still run; Ollama may be tried; analysis continues with degraded/keyword fallbacks if models fail.
- **App still runs?** Yes.
- **Simulate?** Use `seed_demo.py` pre-analyzed traces.
- **Hide in interview?** Yes — seed UI is enough.

### `OLLAMA_BASE_URL` / `OLLAMA_MODEL`

- **Feature:** Local LLM fallback for analysis metrics and investigator polish.
- **If missing/unreachable:** Logged and skipped; core grounding can still use local NLI.
- **App still runs?** Yes.
- **Interview?** No requirement.

### `RAZORPAY_*` / `NEXT_PUBLIC_RAZORPAY_KEY_ID`

- **Feature:** Checkout, webhooks, plan activation.
- **If missing:** `billing.py` refuses client creation; **usage quotas still work** from DB plan fields.
- **App still runs?** Yes.
- **Interview?** Hide checkout; show usage page / seed plan.

### `RESEND_API_KEY` / `SMTP_*`

- **Feature:** Verification and password-reset emails.
- **If missing:** Emails log to console (`email_service.py` returns success in dev fallback).
- **App still runs?** Yes if `REQUIRE_EMAIL_VERIFICATION=false` (or seed user already verified).
- **Interview?** Keep verification off or use seed user.

### `GOOGLE_OAUTH_*` (all three)

- **Feature:** Google SSO (`identity.py` — live only when client id, secret, and redirect URI are set).
- **If missing:** Password login / register only.
- **Interview?** Hide SSO button path; use demo login.

### `SENTRY_DSN` / `OTEL_EXPORTER_OTLP_ENDPOINT`

- **Feature:** Error tracking / tracing.
- **If missing:** structlog only; no export.
- **Interview?** Not needed.

### `OPS_SHARED_TOKEN`

- **Feature:** Protects sensitive ops routes when set.
- **If missing in development:** Ops endpoints accessible without token (by design).
- **Production:** Required by validation.

### Local ML (`EMBEDDING_MODEL_NAME` / `NLI_MODEL_NAME`)

- **Feature:** Sentence grounding / Trust Score on **live** Celery analysis (downloads from Hugging Face Hub into cache — not an API key, but needs network first time).
- **If worker OOM / offline:** Ingest still stores traces; use seed or `reanalyze` later.
- **Interview?** Prefer seed data.

---

## External Services

| Service | Why it exists | Required? | Local alternative | Can disable? |
|---------|---------------|-----------|-------------------|--------------|
| **PostgreSQL** (+ pgvector image) | Primary datastore | **Yes** (Compose) | SQLite only for limited local/non-prod fallback — not for interview Compose | No for Compose stack |
| **Redis** | Celery, denylist, cache, ready check | **Yes** | None in this product | No for healthy `/ready` |
| **Celery worker/beat** | Async analysis + schedules | Recommended for live analysis; **not** for seed UI | Run analysis later / seed | Yes for seed-only demo |
| **Hugging Face Inference API** | Optional LLM metrics | No | Ollama or none | Leave `HF_API_TOKEN` blank |
| **Hugging Face Hub** | Download local NLI/embedding weights | Only for live ML first run | Pre-warmed volume / seed | Seed avoids need |
| **Ollama** | Optional local LLM | No | None | Don’t run Ollama |
| **Resend / SMTP** | Email | No | Console log fallback | Blank keys |
| **Google OAuth** | SSO | No | Password auth | Blank `GOOGLE_OAUTH_*` |
| **Razorpay** | Payments | No | Usage API without checkout | Blank keys |
| **Sentry / OTel** | Observability | No | Logs / `/ops/metrics` | Blank |
| **Prometheus / Grafana** | Compose observability overlay | No | `/ops/metrics` alone | Omit overlay |
| **MinIO / S3 / OpenAI / Groq / Gemini** | — | **Not implemented** | — | N/A |

Slack/Teams/etc. use **user-configured webhooks in the DB**, not env API keys in `Settings`.

---

## Feature Dependency Matrix

| Feature | Needs keys? | Needs infra? | Works with seed only? |
|---------|-------------|--------------|------------------------|
| Login / JWT / RBAC | `SECRET_KEY` | Postgres (+ Redis for denylist) | Yes |
| Dashboard / queries / grounding UI | None | Postgres | **Yes** (seed) |
| API key + ingest | None | Postgres; Redis/Celery for live analysis | Ingest yes; analysis optional |
| Live NLI analysis | None (local models) | Worker + RAM + Redis | Prefer seed if low RAM |
| LLM-enriched metrics | `HF_API_TOKEN` or Ollama | Worker | Optional |
| Billing usage | None | Postgres | Yes |
| Billing checkout | Razorpay keys | — | Hide |
| Email verify / reset | Resend or SMTP | — | Soft-gate or seed |
| Google SSO | Google OAuth trio | — | Hide |
| Ops metrics Prometheus | None | API process | Yes |
| Support admin | `SUPPORT_ADMIN_EMAILS` | — | Optional |

---

## Interview Configuration

**Minimum to demonstrate:**

```text
Infrastructure: Docker Compose → Postgres + Redis + API + frontend (+ worker optional)
Secrets:        SECRET_KEY=<random ≥32 chars>
Everything else: defaults from .env.example / Compose
Email gate:     REQUIRE_EMAIL_VERIFICATION=false
Data:           python scripts/seed_demo.py
Login:          demo@example.com / DemoPass123!
```

**Leave blank:** `HF_API_TOKEN`, Razorpay, Resend/SMTP, Google OAuth, Sentry, OTel.

**Optional low-RAM:** `docker-compose.interview.yml` (`WARM_ML_MODELS_ON_WORKER_START=false`, concurrency=1).

---

## Production Configuration

See `.env.production.example` and `docs/DEPLOYMENT.md`.

Must satisfy `validate_production_settings()`:

- Strong `SECRET_KEY`, HTTPS `FRONTEND_URL`, production `ALLOWED_HOSTS`
- Managed Postgres + Redis URLs (no localhost / default passwords)
- `OPS_SHARED_TOKEN` ≥16 chars
- Prefer `REQUIRE_EMAIL_VERIFICATION=true` + Resend/SMTP for real users
- Vercel: `NEXT_PUBLIC_API_URL=https://<api>`

---

## Example `.env` (interview placeholders — no real secrets)

```bash
# ===== Interview / local demo =====
# Generate: python -c "import secrets; print(secrets.token_urlsafe(32))"
SECRET_KEY=replace-with-at-least-32-char-random-secret
ENVIRONMENT=development
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

FRONTEND_URL=http://localhost:3000
NEXT_PUBLIC_API_URL=http://localhost:8000
ALLOWED_HOSTS=localhost,127.0.0.1
REQUIRE_EMAIL_VERIFICATION=false

# Compose usually overrides these with service DNS (db / redis)
DATABASE_URL=postgresql+asyncpg://raginspector:raginspector_secret@localhost:5432/raginspector
DATABASE_SYNC_URL=postgresql://raginspector:raginspector_secret@localhost:5432/raginspector
POSTGRES_USER=raginspector
POSTGRES_PASSWORD=raginspector_secret
POSTGRES_DB=raginspector

REDIS_URL=redis://:redis_secret@localhost:6379/0
REDIS_PASSWORD=redis_secret

# ----- Optional SaaS keys: LEAVE BLANK for interviews -----
HF_API_TOKEN=
HF_MODEL=HuggingFaceH4/zephyr-7b-beta
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

RAZORPAY_KEY_ID=
RAZORPAY_KEY_SECRET=
RAZORPAY_WEBHOOK_SECRET=
NEXT_PUBLIC_RAZORPAY_KEY_ID=
RAZORPAY_PLAN_STARTER_MONTHLY=
RAZORPAY_PLAN_STARTER_ANNUAL=
RAZORPAY_PLAN_PRO_MONTHLY=
RAZORPAY_PLAN_PRO_ANNUAL=
RAZORPAY_PLAN_ENTERPRISE_MONTHLY=
RAZORPAY_PLAN_ENTERPRISE_ANNUAL=

RESEND_API_KEY=
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM=noreply@raginspector.com

GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=
GOOGLE_OAUTH_REDIRECT_URI=

SENTRY_DSN=
OTEL_EXPORTER_OTLP_ENDPOINT=
OPS_SHARED_TOKEN=
SUPPORT_ADMIN_EMAILS=

# Local ML (no API key; downloads models on first worker analysis)
EMBEDDING_MODEL_NAME=all-MiniLM-L6-v2
NLI_MODEL_NAME=cross-encoder/nli-deberta-v3-small
WARM_ML_MODELS_ON_WORKER_START=false
```

---

## Configuration notes / unused variables

| Finding | Detail |
|---------|--------|
| `LOG_RETENTION_DAYS` | Present in `Settings` / `.env.example`; **no application reader** found (only `LOG_LEVEL` is applied in `logging.py`). |
| `GOOGLE_OAUTH_*` in Compose | Documented in `.env.example` but **not** passed in `docker-compose.yml` `environment:` blocks — set via another inject method or extend Compose if demoing SSO in Docker. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Read via `os.environ` in `otel.py`, **not** a `Settings` field. |
| OpenAI / Groq / Gemini / MinIO | **Not in live code** — ignore PRD mentions. |
| Investigator HF branch | Checks `HF_API_TOKEN` then `pass`es; actually calls **Ollama** for polish (`ai_investigator.py`). |

---

## Final summary

1. **~50** Settings fields + **~15** deploy/compose/test vars + **2** frontend public vars.
2. **Required for interview Compose:** Postgres, Redis, workable `SECRET_KEY` (defaults exist but should be changed); Compose supplies DB/Redis.
3. **Required commercial API keys:** **zero**.
4. **Optional integrations:** HF Inference, Ollama, Razorpay, Resend/SMTP, Google OAuth, Sentry, OTel, Grafana.
5. **External services in product:** Postgres, Redis, optional HF Hub (model download), optional HF Inference, Ollama, Resend/SMTP, Google, Razorpay, Sentry/OTel.
6. **Minimum run:** Compose stack + `SECRET_KEY` + `seed_demo.py` → full UI demo.
7. **Without optional keys:** no SSO, checkout, real email, Sentry, or LLM-enriched metrics; **core debugger UI and seed grounding still work**.
8. **Mistakes / dead config:** `LOG_RETENTION_DAYS` unused; Google OAuth env not wired through default Compose; no OpenAI/Groq/MinIO despite older docs.

**Related:** [`.env.example`](.env.example) · [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) · [`docs/INTERVIEW_DEPLOYMENT.md`](docs/INTERVIEW_DEPLOYMENT.md) · [`docs/SECRETS.md`](docs/SECRETS.md)
