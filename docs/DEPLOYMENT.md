# Deployment Guide

RAGInspector supports three deployment shapes:

| Shape | Use when | Path |
|-------|----------|------|
| **Free cloud (portfolio)** | Interview / demo on the public internet | Vercel (UI) + Render (API + Postgres + Redis) |
| **Docker Compose** | Local interview laptop / self-host VPS | `docker-compose.yml` (+ optional prod/TLS) |
| **Kubernetes / Helm** | Team / enterprise | `infrastructure/helm/raginspector` |

This document is the source of truth for **free cloud** and **Compose**. Helm details live in [`KUBERNETES.md`](KUBERNETES.md) / [`HELM.md`](HELM.md).

**Honesty:** Live Celery NLI analysis needs ~2–3 GB RAM and is a poor fit for free worker tiers. Portfolio demos should use **`scripts/seed_demo.py`** (pre-analyzed traces). Optional worker/beat services are documented but not required for a UI walkthrough.

---

## Architecture (free cloud)

```text
Browser ──► Vercel (Next.js)
               │  NEXT_PUBLIC_API_URL
               ▼
            Render Web (FastAPI) ──► Render Postgres
               │
               ├──► Redis (Render Key Value or Upstash)
               │
               └──► (optional) Celery worker + beat
```

| Component | Platform | Health |
|-----------|----------|--------|
| Frontend | Vercel | Vercel platform checks |
| API | Render Web Service | `GET /live` (or `/health`) |
| Readiness | same | `GET /api/v1/ops/ready` (DB + Redis) |
| Postgres | Render Postgres (free) | managed |
| Redis | Render Key Value or Upstash | required for production validation |
| Worker / Beat | Render Background Worker | optional |

No object storage. No Kubernetes required for portfolio deploy.

---

## Supported platforms

| Platform | Role | Status |
|----------|------|--------|
| **Vercel** | Frontend | Supported — Root Directory `frontend`, see `frontend/vercel.json` |
| **Render** | API + Postgres (+ Redis/worker) | Supported — see root `render.yaml` |
| **Railway** | API/worker alternative | Supported via `backend/Dockerfile` + `backend/Procfile`; set `PORT` |
| **Fly.io** | API alternative | Supported via Docker; set `PORT`; run migrations as a release step |
| **Docker Compose** | Local / VPS | Fully supported |

---

## Environment variables

### Required (cloud API — `ENVIRONMENT=production`)

| Variable | Purpose | Interview / portfolio default | Production recommendation |
|----------|---------|-------------------------------|---------------------------|
| `SECRET_KEY` | JWT + MFA crypto | Generate ≥32 chars | Rotate; secret manager |
| `DATABASE_URL` | Async ORM | Render connection string (auto-normalized to `+asyncpg`, SSL) | Managed Postgres + backups |
| `DATABASE_SYNC_URL` | Alembic / Celery sync | Same host as above (sync driver) | Same |
| `REDIS_URL` | Celery + denylist + cache | Upstash / Render Redis URL | Auth + TLS if offered |
| `FRONTEND_URL` | CORS Origin (exact) | `https://<app>.vercel.app` | Custom domain HTTPS |
| `ALLOWED_HOSTS` | TrustedHost | `raginspector-api.onrender.com` | API hostname(s) |
| `OPS_SHARED_TOKEN` | Ops endpoints | ≥16 random chars | Strong secret |
| `REQUIRE_EMAIL_VERIFICATION` | Login gate | **`false`** without mail provider | `true` + Resend/SMTP |

### Required (Vercel)

| Variable | Purpose | Notes |
|----------|---------|-------|
| `NEXT_PUBLIC_API_URL` | Browser → API | `https://<api>.onrender.com` — must be set **before** build |

### Optional (leave blank for demos)

| Variable | Feature if set | Works if blank? | UI when unavailable |
|----------|----------------|-----------------|---------------------|
| `HF_API_TOKEN` | LLM judge metrics | Yes | Analysis uses local NLI only |
| `OLLAMA_*` | Local LLM fallback | Yes | Skipped |
| `RAZORPAY_*` | Checkout | Yes | Billing usage still shows; checkout disabled |
| `RESEND_*` / `SMTP_*` | Email | Yes | Verification/reset emails not sent |
| `GOOGLE_OAUTH_*` | SSO | Yes | Password login only |
| `SENTRY_DSN` | Error tracking | Yes | structlog only |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Tracing | Yes | No export |

Templates: [`.env.example`](../.env.example), [`.env.production.example`](../.env.production.example).

### Cloud URL notes

- Render injects `postgresql://…`. The API **normalizes** to `postgresql+asyncpg://…` and adds TLS query params in production (`app.core.config.normalize_database_urls`).
- Do **not** point production at `localhost` or default passwords (`raginspector_secret` / `redis_secret`) — `validate_production_settings()` fails closed.
- Prefer platform health check on **`/live`**, not `/api/v1/ops/ready` (Redis blips would otherwise restart the web service).

---

## Free cloud deploy (Vercel + Render)

### Checklist

1. **Create Redis** (Upstash free or Render Key Value). Copy `REDIS_URL`.
2. **Deploy API** via Render Blueprint (`render.yaml`) or manual Docker web service from `backend/`.
3. Set API env: `SECRET_KEY`, `OPS_SHARED_TOKEN`, `REDIS_URL`, `FRONTEND_URL` (placeholder OK until Vercel exists), `ALLOWED_HOSTS=<api-host>`, `REQUIRE_EMAIL_VERIFICATION=false`, `RUN_MIGRATIONS=1`, `UVICORN_WORKERS=1`.
4. Confirm `GET https://<api>/live` → 200 and `GET https://<api>/api/v1/ops/ready` → ready (after Redis set).
5. **Deploy frontend** on Vercel: Root Directory = `frontend`, env `NEXT_PUBLIC_API_URL=https://<api>`.
6. Update API `FRONTEND_URL=https://<vercel-app>` and redeploy API (CORS).
7. **Seed demo** (one-off Render shell or local against prod DB):

   ```bash
   # from backend image / shell with DATABASE_* set
   python scripts/seed_demo.py
   ```

8. Login at Vercel URL: `demo@example.com` / `DemoPass123!`
9. Verify dashboard, queries, grounding UI.
10. (Optional) Enable worker/beat only if Redis + RAM allow; set `WARM_ML_MODELS_ON_WORKER_START=false`.

### Expected outcomes / failures

| Step | Expected | Failure symptoms | Fix |
|------|----------|------------------|-----|
| API boot | `/live` 200 | Crash loop | Check logs for production validation; set Redis/HTTPS FRONTEND_URL/hosts |
| Migrations | Tables present | 500 on login | `RUN_MIGRATIONS=1` or run `alembic upgrade head` |
| Ready | `database=ok`, `redis=ok` | 503 | Fix `DATABASE_*` / `REDIS_URL` (+ SSL) |
| CORS login | Browser login works | Network/CORS error | Exact `FRONTEND_URL` match; rebuild Vercel if API URL wrong |
| Seed login | Dashboard data | Empty metrics | Re-run `seed_demo.py` |
| Worker | Live analysis | OOM / stuck analyzing | Stay on seed; or upgrade worker RAM |

### Render Blueprint

```bash
# In Render dashboard: New → Blueprint → select this repo → render.yaml
```

Services defined:

- `raginspector-db` (Postgres free)
- `raginspector-api` (web, Docker, `/live`, `RUN_MIGRATIONS=1`)
- `raginspector-worker` / `raginspector-beat` (optional; starter plan — disable if over budget)

Manual start commands (non-Docker):

```bash
# web
sh scripts/start_api.sh          # honors $PORT

# worker / beat
sh scripts/start_worker.sh
sh scripts/start_beat.sh
```

See `backend/Procfile` for Railway-style process types.

### Vercel

1. Import repo → **Root Directory: `frontend`**
2. Framework: Next.js (see `frontend/vercel.json`)
3. Env: `NEXT_PUBLIC_API_URL=https://<your-api>`
4. Node **20.x** (`engines` in `frontend/package.json`)
5. Deploy → copy URL into Render `FRONTEND_URL`

### Railway / Fly.io (optional)

Same Docker image (`backend/Dockerfile`):

- Bind: `start_api.sh` uses `PORT`
- Release/migrate: `alembic upgrade head` or `RUN_MIGRATIONS=1`
- Attach managed Postgres + Redis
- Set the same production env vars as Render

---

## Docker Compose (local / VPS)

### Interview / local (dev)

```bash
cp .env.example .env   # set SECRET_KEY
# Windows busy ports:
docker compose -f docker-compose.yml -f docker-compose.verify-ports.yml -f docker-compose.interview.yml up -d --build
docker compose -f docker-compose.yml -f docker-compose.verify-ports.yml run --rm backend alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.verify-ports.yml run --rm backend python scripts/seed_demo.py
```

Full interview guide: [`INTERVIEW_DEPLOYMENT.md`](INTERVIEW_DEPLOYMENT.md).

### Production Compose

```bash
cp .env.production.example .env.production
# fill required secrets

docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm backend alembic upgrade head
```

Details: [`COMPOSE_PROD.md`](COMPOSE_PROD.md). TLS: [`TLS.md`](TLS.md).

### Startup automation

| Mechanism | Behavior |
|-----------|----------|
| `RUN_MIGRATIONS=1` | `docker-entrypoint.sh` runs `alembic upgrade head` before CMD |
| `scripts/start_api.sh` | `uvicorn --host 0.0.0.0 --port $PORT` |
| Compose `make bootstrap` / `scripts/bootstrap.ps1` | build → wait `/live` → migrate |

Production does **not** auto-`create_all`; Alembic owns schema.

---

## Docker quality notes

| Image | Notes |
|-------|--------|
| `backend/Dockerfile` | Multi-stage; CPU torch; non-root `app`; `PORT`-aware healthcheck `/live` |
| `frontend/Dockerfile` | Node 20 Alpine; Next `standalone` for containers (Vercel ignores this) |
| Workers | Same backend image; override CMD with `start_worker.sh` / `start_beat.sh` |

---

## Security (cloud)

- Production fail-closed: strong `SECRET_KEY`, HTTPS `FRONTEND_URL`, non-localhost hosts/DB/Redis, `OPS_SHARED_TOKEN`.
- CORS in production locks to a **single** `FRONTEND_URL` origin.
- `/docs` and `/redoc` disabled when `ENVIRONMENT=production`.
- Do not set `REQUIRE_EMAIL_VERIFICATION=false` on a real customer deployment without understanding the risk.
- Rotate any secret that ever lived in a local `.env` — see [`SECURITY.md`](../SECURITY.md).

---

## Optional integrations

| Integration | Enables | Deploy without it? | Disable | UI if unavailable |
|-------------|---------|--------------------|---------|-------------------|
| Hugging Face Inference | LLM judge | Yes | Blank `HF_API_TOKEN` | Core NLI still runs (with worker) |
| Ollama | Local LLM | Yes | Don’t run Ollama | Skipped |
| Razorpay | Payments | Yes | Blank keys | Usage page; no checkout |
| Resend / SMTP | Email | Yes | Blank | No verify/reset mail |
| Google OAuth | SSO | Yes | Blank | Password auth |
| Sentry / OTel | APM | Yes | Blank | Logs only |
| Slack/Teams webhooks | Alerts | Yes | Don’t configure | No outbound alerts |

OpenAI / Groq / Gemini / MinIO are **not** in the live product (PRD archive only).

---

## Updating & rollback

### Update

1. Merge to main / deploy branch.
2. Vercel auto-builds frontend (confirm `NEXT_PUBLIC_API_URL`).
3. Render redeploys API (migrations via `RUN_MIGRATIONS=1` or release command).
4. Smoke: `/live`, login, dashboard.

### Rollback

1. **Vercel:** Promote previous deployment in the dashboard.
2. **Render:** Rollback deploy; if a migration is unsafe, restore Postgres from backup before rolling app back — see [`DISASTER_RECOVERY.md`](DISASTER_RECOVERY.md).
3. **Compose:** `git checkout <tag>` + `docker compose … up -d --build`; restore DB dump if schema moved forward.

---

## Manual cloud test plan

| # | Step | Expected | Failure | Troubleshooting |
|---|------|----------|---------|-----------------|
| 1 | Provision Postgres | Connection string issued | Quota / region | Recreate free DB |
| 2 | Provision Redis | `REDIS_URL` works | Auth fail | Check password / TLS URL |
| 3 | Set API env vars | Validation passes | Crash: Invalid production configuration | Fix SECRET/FRONTEND/HOSTS/DB/REDIS/OPS |
| 4 | Deploy API | `/live` 200 | Build OOM | Keep free web; don’t warm ML on API |
| 5 | Migrations | `/ready` migrations soft-check OK | Relation missing | `alembic upgrade head` |
| 6 | Deploy Vercel | UI loads | Blank / 500 | Root=`frontend`, Node 20 |
| 7 | CORS | Login succeeds | Blocked by CORS | Match `FRONTEND_URL` exactly |
| 8 | Seed | Demo user works | 401 | Re-seed; check verification flag |
| 9 | Dashboard | Charts / queries | Empty | Seed; check API URL in browser network tab |
| 10 | Restart API | Data persists | Data loss | Confirm managed Postgres disk |
| 11 | Logs | Structured JSON | Silence | Render log stream |
| 12 | Metrics | `/api/v1/ops/metrics` text | 401/404 | Ungated path; protect at edge if public |

---

## Production considerations (beyond free tier)

- Keep email verification on; configure Resend.
- Run worker + beat with adequate RAM; `WARM_ML_MODELS_ON_WORKER_START=true` when sized.
- TLS at platform edge; custom domains.
- Backups + restore drill ([`DISASTER_RECOVERY.md`](DISASTER_RECOVERY.md)).
- Sentry + uptime on `/live`.
- Razorpay only with real keys and webhook URL `https://api…/api/v1/billing/webhook`.

---

## Known limitations

1. Free Render workers often **cannot** load NLI models — use seed data for demos.
2. Vercel preview URLs need a matching `FRONTEND_URL` (single-origin CORS).
3. Cold starts on free Render web tiers can take many seconds.
   Mitigate with the GitHub keep-alive workflow — see [`render_keepalive.md`](render_keepalive.md).
4. First HF model download on a worker is slow and disk-heavy.
5. Helm/K8s path is optional and **not** required for portfolio cloud deploy.

---

## Interview deployment (local)

Prefer Compose + seed — fastest path for hiring managers:

[`INTERVIEW_DEPLOYMENT.md`](INTERVIEW_DEPLOYMENT.md)

Demo login: `demo@example.com` / `DemoPass123!`

---

## Compose production checklist (self-host)

### 1. Rotate exposed secrets

Rotate every secret that has ever lived in a local `.env`:

- `SECRET_KEY`, `HF_API_TOKEN`, Razorpay, SMTP/Resend, Postgres, Redis

### 2. Configure production environment

Use `.env.production.example`. Required:

- `ENVIRONMENT=production`
- `FRONTEND_URL=https://yourdomain.com`
- `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`
- `ALLOWED_HOSTS=api.yourdomain.com`
- `DATABASE_URL` / `DATABASE_SYNC_URL` / `REDIS_URL`
- `SECRET_KEY` / `OPS_SHARED_TOKEN`

HTTP security headers and CORS: [`SECURITY.md`](../SECURITY.md).

### 3. Provision infrastructure

PostgreSQL + Redis + HTTPS termination. Compose prod: [`COMPOSE_PROD.md`](COMPOSE_PROD.md). TLS: [`TLS.md`](TLS.md).

### 4. Run migrations

```bash
cd backend && alembic upgrade head
# or RUN_MIGRATIONS=1 on the web container
```

### 5. Workers

[`COLD_START.md`](COLD_START.md), [`WORKER.md`](WORKER.md).

### 6. Email

Prefer `RESEND_API_KEY`. Production should keep `REQUIRE_EMAIL_VERIFICATION=true` when mail works.

### 7. Verify release

```bash
cd backend && python -m pytest tests/unit/ -q
cd ../frontend && npm run build
curl -fsS "$API_URL/live"
curl -fsS "$API_URL/api/v1/ops/ready"
```

Optional: `python scripts/validate_release.py`

### 8. Ops baseline

- `/live`, `/health` — liveness  
- `/api/v1/ops/ready` — readiness (503 if DB/Redis down)  
- `/api/v1/ops/metrics` — Prometheus text  
- Optional Sentry via `SENTRY_DSN`

---

## Related

- [`INTERVIEW_DEPLOYMENT.md`](INTERVIEW_DEPLOYMENT.md) — local interview stack  
- [`SECRETS.md`](SECRETS.md) — secret handling  
- [`WINDOWS.md`](WINDOWS.md) — port overlays  
- [`EXPERIMENTAL.md`](EXPERIMENTAL.md) — partial features  
