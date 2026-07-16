# Security

Security control summary for operators and reviewers. Complementary docs: [SECRETS.md](../SECRETS.md), [COMPLIANCE.md](../COMPLIANCE.md), [API_KEYS.md](../API_KEYS.md).

## Authentication & authorization

- Passwords hashed with the project’s configured password hasher (see `app/core/security.py`).
- Access + refresh tokens; refresh hashes stored server-side and revoked on logout.
- API keys stored hashed; plaintext shown once at creation; rotation supported.
- Role checks via dependencies (`require_role` patterns) for admin/audit/SSO.
- Email verification and MFA available for hardened deployments.
- Enterprise: OIDC/SAML SSO, org `sso_required` / `mfa_required`.

## Transport & HTTP

- TLS at ingress in production ([TLS.md](../TLS.md)).
- Security headers middleware (`app/core/security_http.py`).
- CORS locked to `FRONTEND_URL` in production.
- TrustedHostMiddleware when `ENVIRONMENT=production`.
- Request IDs for forensic correlation — no secrets in logs.

## Abuse controls

- SlowAPI rate limits on auth and ingest ([API.md](../API.md)).
- Plan gates and monthly trace quotas.
- Optional IP allowlists (`ip_allowlist` module) where configured.

## Data protection

- Minimize PII in traces; treat query/answer text as sensitive customer data.
- Encrypt secrets at rest where secret encryption helpers apply.
- Postgres backups encrypted in transit/rest per cloud provider settings.
- Disable public `/docs` in production.

## Dependency & supply chain

- `make security-bandit` for Python SAST.
- `make sbom` for CycloneDX inventories ([SUPPLY_CHAIN.md](../SUPPLY_CHAIN.md)).
- Pin images in prod compose; scan in CI when available.

## Audit

- Org admin audit log API for sensitive actions.
- Retain logs per customer policy; scrub tokens from structured log fields.

## Reporting issues

Prefer private disclosure to maintainers; do not file public issues with exploit PoCs against production. Provide request ids, versions, and reproduction without live secrets.
