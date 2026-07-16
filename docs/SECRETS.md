# Secrets management

## Precedence

1. **Environment / Kubernetes Secret** (highest for runtime)
2. Config files / ConfigMap (non-secret only)
3. Application defaults

Production ConfigMaps must never contain passwords, API keys, or connection strings with credentials.

## Kubernetes

Create Opaque Secret `raginspector-secrets` **before** production/staging Helm installs (`secret.create: false`):

| Key | Required | Notes |
|-----|----------|-------|
| `SECRET_KEY` | yes | ≥32 chars; JWT signing |
| `DATABASE_URL` | yes | `postgresql+asyncpg://…` |
| `DATABASE_SYNC_URL` | yes | sync/psycopg URL for Alembic/Celery |
| `REDIS_URL` | yes | `redis://:password@host:6379/0` |
| `OPS_SHARED_TOKEN` | recommended | Gates `/ops/metrics` & backlog |
| `HF_API_TOKEN` | optional | Hugging Face |
| `SENTRY_DSN` | optional | |
| SMTP / Razorpay keys | optional | Billing/email |

```bash
kubectl -n raginspector create secret generic raginspector-secrets \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=DATABASE_URL='…' \
  --from-literal=DATABASE_SYNC_URL='…' \
  --from-literal=REDIS_URL='…' \
  --from-literal=OPS_SHARED_TOKEN="$(openssl rand -hex 24)"
```

### External providers (future-ready)

Example: `infrastructure/kubernetes/examples/externalsecret.yaml` (External Secrets Operator).
Also support Docker Compose via `.env.production` (never commit), and cloud secret managers injecting env at deploy time.

## Docker Compose

- Dev: `.env` (gitignored)
- Prod: `.env.production` + `--env-file`
- `OPS_SHARED_TOKEN` is wired into `docker-compose.prod.yml` `x-backend-env`

## Rotation procedures

### JWT `SECRET_KEY`

1. Deploy new key only after coordinated session invalidation window.
2. Update Secret / env; rolling restart API + workers + beat.
3. Expect all sessions/tokens to invalidate — communicate change window.
4. Verify login works; old tokens must 401.

### Database / Redis passwords

1. Rotate on managed service.
2. Update Secret URLs.
3. `kubectl rollout restart` backend, worker, beat (migrate Job not required for password-only).
4. Confirm `/api/v1/ops/ready` returns 200.

### API keys (`ri-…` application keys)

See `docs/API_KEYS.md` — revoke in UI/admin, create replacement, update SDK clients.

### `OPS_SHARED_TOKEN`

1. Generate new token; update Secret + Prometheus scrape bearer.
2. Restart API pods; update ServiceMonitor bearer.
3. Old scrapes will 401 until Prometheus config refreshes.

## Hard rules

- Never log secret values (structlog redaction expected for password/token fields).
- Never return secrets from APIs.
- Never commit `.env*` with real values.
- Mask diagnostics: ops endpoints do not echo connection strings.
- Fail-fast: `ENVIRONMENT=production` runs `validate_production_settings()` at API startup.
