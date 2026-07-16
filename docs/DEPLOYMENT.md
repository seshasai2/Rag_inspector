# Production Deployment Checklist

## 1. Rotate Exposed Secrets

Rotate every secret that has ever lived in a local `.env` or terminal output:

- `SECRET_KEY`
- `HF_API_TOKEN`
- Razorpay keys and webhook secret
- SMTP or Resend credentials
- Postgres password
- Redis password

## 2. Configure Production Environment

Use `.env.production.example` as the source of required variables. Store real values in your host's secret manager, not in git.

HTTP security headers and CORS: see [`SECURITY.md`](../SECURITY.md).

Required production values:

- `ENVIRONMENT=production`
- `FRONTEND_URL=https://yourdomain.com` (HTTPS, no trailing slash — CORS Origin match)
- `NEXT_PUBLIC_API_URL=https://api.yourdomain.com`
- `ALLOWED_HOSTS=api.yourdomain.com`
- `SUPPORT_ADMIN_EMAILS=admin@yourdomain.com`
- `SENTRY_DSN`, if using Sentry
- `DATABASE_URL`
- `DATABASE_SYNC_URL`
- `REDIS_URL`
- `SECRET_KEY`

## 3. Provision Infrastructure

- PostgreSQL with backups enabled
- Redis with authentication
- HTTPS termination through Caddy, Nginx plus Let's Encrypt, Cloudflare, or a managed load balancer
- Persistent volumes for database and Redis if using Docker

### Docker Compose production file (Phase 8.1)

Use **`docker-compose.prod.yml`**: no host bind mounts, resource limits, `restart: unless-stopped`, secrets required. Details: [`COMPOSE_PROD.md`](COMPOSE_PROD.md).

```bash
cp .env.production.example .env.production
# fill required secrets

docker compose -f docker-compose.prod.yml --env-file .env.production up -d --build
docker compose -f docker-compose.prod.yml --env-file .env.production run --rm backend alembic upgrade head
```

### HTTPS / TLS (Phase 8.2)

Documented end-to-end path: [`TLS.md`](TLS.md).

- Sample config: `nginx/nginx.tls.conf`
- Overlay: `docker-compose.prod.tls.yml` (ports 80 + 443, certs from `./certs`)
- Local certs: `.\scripts\gen-dev-certs.ps1` or `./scripts/gen-dev-certs.sh`

```bash
# after filling .env.production with https:// URLs
./scripts/gen-dev-certs.sh   # or PowerShell equivalent
docker compose \
  -f docker-compose.prod.yml \
  -f docker-compose.prod.tls.yml \
  --env-file .env.production \
  up -d --build
```

For production domains, use Let's Encrypt (or terminate TLS at Cloudflare / a load balancer) as described in `TLS.md`.

## 4. Run Migrations

Production startup does not auto-create tables. Run this before starting the app:

```bash
cd backend
alembic upgrade head
```

## 5b. ML models (analysis workers)

See [`docs/COLD_START.md`](COLD_START.md). Prefetch Hugging Face weights, keep `WARM_ML_MODELS_ON_WORKER_START=true` on Celery workers, and size RAM for one copy of NLI + embeddings **per worker process**.

## 5c. Worker concurrency & backlog

See [`docs/WORKER.md`](WORKER.md). Default Compose worker uses `--concurrency=2` and listens to **`analysis,celery`**. Prefer horizontal replicas over high concurrency when ML models dominate RAM. Monitor backlog via `GET /api/v1/ops/backlog` or Prometheus gauges on `GET /api/v1/ops/metrics`.

Create Razorpay plans and set:

- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`
- all `RAZORPAY_PLAN_*` values

Set the Razorpay webhook URL to:

```text
https://api.yourdomain.com/api/v1/billing/webhook
```

Subscribe to subscription lifecycle events, including activated, cancelled, and halted.

## 6. Configure Email

Prefer `RESEND_API_KEY`, or configure SMTP:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`

### Email verification before login

| Setting | Behavior |
|---------|----------|
| `REQUIRE_EMAIL_VERIFICATION=true` | Login returns **403** until the user verifies via `/api/v1/auth/verify-email`. Resend with `POST /api/v1/auth/resend-verification` `{ "email": "..." }` (no auth required). |
| `REQUIRE_EMAIL_VERIFICATION=false` | Soft-gate: registration still sends a verification email, but login is allowed without verifying. |
| unset | Defaults to **true** when `ENVIRONMENT=production`, otherwise **false** (local/dev/test). |

Production should keep verification required (`true` or rely on the production default) and configure a real mail provider.

Smoke test:

- register
- verify email
- forgot password
- reset password
- login
- (optional) confirm unverified login is blocked when the hard-gate is on
- (optional) with MFA enrolled: password-only login returns `mfa_required` (no tokens); `/auth/login/mfa` completes the session

## 7. Verify The Release

Run locally or in CI:

```bash
cd backend && python -m pytest tests/unit/ -q
cd ../frontend && npm run build
cd .. && docker compose config --quiet
```

After deploy:

```bash
docker compose up --build -d
docker compose logs --tail 100 backend
docker compose logs --tail 100 frontend
docker compose logs --tail 100 celery_worker
```

### Kubernetes (Phase 3A.2)

Preferred enterprise path — cloud-agnostic Helm chart:

- Chart: `infrastructure/helm/raginspector`
- Docs: [`KUBERNETES.md`](KUBERNETES.md), [`HELM.md`](HELM.md), [`SECRETS.md`](SECRETS.md), [`RUNBOOKS.md`](RUNBOOKS.md)
- Pre-deploy Secrets; then:

```bash
helm upgrade --install raginspector ./infrastructure/helm/raginspector \
  -f ./infrastructure/helm/raginspector/values-production.yaml \
  -n raginspector --create-namespace
API_URL=https://api.example.com FRONTEND_URL=https://app.example.com \
  python scripts/validate_release.py
```

## 8. End-To-End Smoke Test

- Login/register works
- Email verification works
- API key creation works
- SDK sends a trace
- Celery worker analyzes the trace
- Dashboard shows the trace
- Billing checkout opens
- Razorpay webhook updates subscription
- Monthly trace limits are enforced

## 9. Operational Baseline

This repo includes:

- Docker JSON log rotation
- Structured JSON logs + `X-Request-ID` end-to-end — [`LOGGING.md`](LOGGING.md)
- a Postgres backup sidecar writing compressed dumps to the `postgres_backups` volume — [`DISASTER_RECOVERY.md`](DISASTER_RECOVERY.md)
- `/api/v1/ops/ready` readiness checks (**HTTP 503** when DB/Redis fail — Compose healthcheck)
- `/health` and `/live` process liveness (always 200 if the API process is up)
- Compose healthchecks for backend / frontend / celery_worker — see [`COMPOSE_HEALTH.md`](COMPOSE_HEALTH.md)
- `/api/v1/ops/metrics` Prometheus-style metrics (uptime + Celery/analysis backlog)
- `/api/v1/ops/backlog` JSON queue depths and job/trace backlog counts
- worker concurrency guidance: [`WORKER.md`](WORKER.md)
- optional Sentry (`SENTRY_DSN`) on API + Celery workers — see below
- production config fail-closed via `validate_production_settings()` (API + workers)
- support admin endpoints protected by `SUPPORT_ADMIN_EMAILS`

### Sentry (optional)

1. Set `SENTRY_DSN` in `.env` / `.env.production`.
2. Restart `backend` and `celery_worker` (both call `init_sentry`).
3. Dev-only smoke: raise an unhandled exception in a throwaway route and confirm the event in Sentry; or rely on unit tests in `tests/unit/test_sentry_init.py`.

Before charging customers, confirm:

- database backups and restore test ([`DISASTER_RECOVERY.md`](DISASTER_RECOVERY.md))
- uptime monitor
- error tracking such as Sentry
- structured log retention
- alerting for failed Celery jobs
- admin/support workflow
- Terms, Privacy Policy, and Refund/Cancellation Policy
