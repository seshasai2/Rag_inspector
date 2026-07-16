# Required API Keys And Secrets

Do not paste real values into chat or commit them to git. Use `.env` locally and a secret manager in production.

**Canonical guide + checklist:** [`SECURITY.md`](../SECURITY.md) (Phase 5.8).
**Templates:** [`.env.example`](../.env.example), [`.env.production.example`](../.env.production.example).

## Required

- `SECRET_KEY`: JWT signing key.
- `DATABASE_URL`: async PostgreSQL URL.
- `DATABASE_SYNC_URL`: sync PostgreSQL URL for Alembic.
- `REDIS_URL`: Celery broker/cache URL.
- `FRONTEND_URL`: public frontend URL.
- `NEXT_PUBLIC_API_URL`: public API URL.
- `ALLOWED_HOSTS`: comma-separated API hostnames.

## Billing

- `RAZORPAY_KEY_ID`
- `RAZORPAY_KEY_SECRET`
- `RAZORPAY_WEBHOOK_SECRET`
- `NEXT_PUBLIC_RAZORPAY_KEY_ID`
- `RAZORPAY_PLAN_STARTER_MONTHLY`
- `RAZORPAY_PLAN_STARTER_ANNUAL`
- `RAZORPAY_PLAN_PRO_MONTHLY`
- `RAZORPAY_PLAN_PRO_ANNUAL`
- `RAZORPAY_PLAN_ENTERPRISE_MONTHLY`
- `RAZORPAY_PLAN_ENTERPRISE_ANNUAL`

## Email

Preferred:

- `RESEND_API_KEY`

SMTP fallback:

- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USER`
- `SMTP_PASSWORD`
- `SMTP_FROM`

## AI Analysis

Cloud option:

- `HF_API_TOKEN`
- `HF_MODEL`

Local option:

- `OLLAMA_BASE_URL`
- `OLLAMA_MODEL`

## Customer-Provided Integrations

Slack alerts use customer-provided incoming webhook URLs stored from the Settings page. You do not need a global Slack API key.
