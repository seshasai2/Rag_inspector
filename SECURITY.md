# Security

Operational security for RAGInspector: HTTP hardening (Phase 5.7) and **secrets management** (Phase 5.8).

---

## Secrets management

### Rules

1. **Never commit secrets.** `.env`, private keys, service-account JSON, and credential dumps stay out of git (see `.gitignore`).
2. **Templates only in git:** `.env.example` (local) and `.env.production.example` (prod shape). Values are placeholders or empty.
3. **Production:** load secrets from the host secret manager / platform env (Docker secrets, AWS SM, GCP Secret Manager, Railway/Render/Fly env, etc.) — not from a committed file.
4. **Rotate** any secret that has appeared in chat, screenshots, CI logs, or a leaked `.env`.
5. **Session revoke:** logout revokes the refresh token in Postgres and, when an `access_token` is supplied, denylists its `jti` in Redis until natural expiry. Use `revoke_all_sessions: true` to invalidate every refresh token for the user.
6. **Public vs secret:** `NEXT_PUBLIC_*` values are bundled into the browser — never put private API secrets there. Razorpay **key id** may be public; **key secret** and **webhook secret** must not.

### Where secrets live

| Environment | Store |
|-------------|--------|
| Local development | `.env` (gitignored), copied from `.env.example` |
| Docker Compose local | `.env` + compose `${VAR:-dev_default}` placeholders |
| Production | Secret manager / host env from `.env.production.example` keys |
| Customer Slack webhooks | Stored per-user in DB from Settings (not a global env secret) |

### Secret inventory

| Variable | Sensitivity | Notes |
|----------|-------------|--------|
| `SECRET_KEY` | **Critical** | JWT + Fernet MFA encryption. ≥32 chars; never the repo default in prod. |
| `DATABASE_URL` / `DATABASE_SYNC_URL` | **Critical** | Includes DB password. |
| `POSTGRES_PASSWORD` | **Critical** | Compose / DB bootstrap. |
| `REDIS_URL` / `REDIS_PASSWORD` | **High** | Broker + cache. |
| `RAZORPAY_KEY_SECRET` | **Critical** | Server-only. |
| `RAZORPAY_WEBHOOK_SECRET` | **Critical** | Webhook HMAC. |
| `RAZORPAY_KEY_ID` / `NEXT_PUBLIC_RAZORPAY_KEY_ID` | Low (public id) | Safe in frontend if using publishable key id. |
| `RESEND_API_KEY` / `SMTP_PASSWORD` | **High** | Mail delivery. |
| `HF_API_TOKEN` | **High** | Inference API. |
| `SENTRY_DSN` | Medium | Project DSN (prefer restricted DSN). |
| `SUPPORT_ADMIN_EMAILS` | Low | Allowlist, not a credential. |

Plan IDs (`RAZORPAY_PLAN_*`) are configuration, not credentials, but keep them out of public docs if you treat them as private.

### `.env.example` completeness

`.env.example` documents every `Settings` field in `backend/app/core/config.py`, plus compose-only keys (`POSTGRES_*`, `REDIS_PASSWORD`, `NEXT_PUBLIC_*`, `BACKUP_RETENTION_DAYS`). CI/unit test: `tests/unit/test_env_example_complete.py`.

### Pre-production secrets checklist

- [ ] `.env` is not tracked; only `.env.example` / `.env.production.example` are in the repo
- [ ] `SECRET_KEY` generated fresh (`secrets.token_urlsafe(32)`) and stored in the secret manager
- [ ] Default compose passwords (`raginspector_secret`, `redis_secret`) **not** used in production
- [ ] `DATABASE_*` and `REDIS_*` use strong unique passwords
- [ ] Razorpay secret + webhook secret set; webhook URL points at production API
- [ ] Email provider configured (`RESEND_API_KEY` or SMTP)
- [ ] `FRONTEND_URL` is HTTPS with **no trailing slash**; `ALLOWED_HOSTS` lists API hosts only
- [ ] No `NEXT_PUBLIC_*` variable holds a private secret
- [ ] Old/leaked keys rotated (JWT secret rotation logs everyone out — plan a maintenance window)
- [ ] Backups of Postgres exclude shipping `.env` alongside DB dumps in public buckets

### If a secret leaks

1. Rotate the credential at the provider (Razorpay, Resend, HF, DB password, Redis).
2. Replace `SECRET_KEY` (invalidates sessions / MFA ciphertext encrypted with the old key — users may need to re-enroll MFA).
3. Revoke exposed user API keys via the dashboard / admin tools.
4. Review audit logs for abuse after the leak window.

---

## Production CORS (API)

Configured in `backend/app/core/security_http.py` and applied from `backend/app/main.py`.

| Setting | Production | Development |
|---------|------------|-------------|
| `allow_origins` | Exact `FRONTEND_URL` only (trailing slash stripped) | `FRONTEND_URL` + localhost variants |
| `allow_origin_regex` | Disabled | `http(s)://127.0.0.1:<port>` |
| `allow_credentials` | `true` | `true` |
| `allow_methods` | `GET, POST, PUT, PATCH, DELETE, OPTIONS` | `*` |
| `allow_headers` | `Authorization`, `Content-Type`, `Accept`, `X-API-Key`, `X-Requested-With` | `*` |

### Operator checklist (CORS / hosts)

1. Set `ENVIRONMENT=production`.
2. Set `FRONTEND_URL=https://app.example.com` — **HTTPS**, **no trailing slash**, must match the browser Origin exactly.
3. Set `ALLOWED_HOSTS` to API hostnames only — enables `TrustedHostMiddleware`.
4. Do **not** list `*` or localhost in production CORS origins.
5. OpenAPI `/docs` and `/redoc` are disabled when `ENVIRONMENT=production`.

Startup also rejects weak production config via `validate_production_settings()` in `app.core.config` (API lifespan + Celery worker init): weak `SECRET_KEY`, non-HTTPS `FRONTEND_URL`, localhost hosts/DB, and default development DB/Redis passwords.

## Security headers (API)

| Header | Value | Notes |
|--------|-------|-------|
| `X-Content-Type-Options` | `nosniff` | Always |
| `X-Frame-Options` | `DENY` | Always |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | Always |
| `Permissions-Policy` | camera/mic/geo disabled | Always |
| `Content-Security-Policy` | `default-src 'none'; frame-ancestors 'none'; …` | API-appropriate |
| `Strict-Transport-Security` | `max-age=63072000; includeSubDomains; preload` | **Production only** |

## Security headers (Frontend)

`frontend/next.config.js` sets browser headers, including a CSP that allows Razorpay checkout. Tighten `connect-src` to the real API origin after deploy.

## Review summary

| Area | Status |
|------|--------|
| CORS locked to `FRONTEND_URL` in production | Done (5.7) |
| Security headers + HSTS | Done (5.7) |
| Secrets guide + checklist | Done (5.8) |
| `.env.example` complete vs `Settings` | Done (5.8) |
| `.gitignore` blocks `.env` / keys; allows example templates | Done (5.8) |
| Audit logging for auth / keys / plan / admin | Done (5.9) |

## Audit logging (Phase 5.9)

Security-relevant actions are written to `audit_logs` via `app.services.audit.record_audit` and queried at `GET /api/v1/audit-logs` (org admin + enterprise plan).

| Surface | Actions |
|---------|---------|
| Auth | `auth.register`, `auth.login`, `auth.logout`, `auth.email_verified`, `auth.password_changed`, `auth.password_reset` |
| API keys | `api_key.created`, `api_key.revoked`, `api_key.rotated` (`POST /keys/{id}/rotate`) |
| Plan / billing | `billing.subscription_created`, `billing.subscription_cancelled`, `billing.plan_changed` (Razorpay webhooks) |
| Support admin | `support.user_status_changed`, `support.impersonation_requested` |

Query filters: `?action=`, `?target_type=`, `?since=` (ISO datetime), `?limit=`.

## Related

- Deployment checklist: `docs/DEPLOYMENT.md`
- Key inventory (short): `docs/API_KEYS.md`
- Env templates: `.env.example`, `.env.production.example`
