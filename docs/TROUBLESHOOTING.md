# Troubleshooting

Quick links for common failures. Prefer measured symptoms over speculation.

## Start here

| Symptom | Guide |
|---------|-------|
| Windows Docker / Make issues | [WINDOWS.md](WINDOWS.md) · `scripts/setup.ps1` · `scripts/bootstrap.ps1` |
| Demo walkthrough failures | [demo/TROUBLESHOOTING.md](demo/TROUBLESHOOTING.md) |
| Worker backlog / Celery | [WORKER.md](WORKER.md) · [RUNBOOKS.md](RUNBOOKS.md) |
| Logging / request IDs | [LOGGING.md](LOGGING.md) |
| Ops day-2 | [engineering/OPERATIONS.md](engineering/OPERATIONS.md) |
| Security / secrets | [../SECURITY.md](../SECURITY.md) |
| Experimental surfaces | [EXPERIMENTAL.md](EXPERIMENTAL.md) |

## Stack won't start

1. Confirm Docker Desktop is running (`docker compose version`).
2. Ensure `.env` exists with `SECRET_KEY` ≥ 32 characters.
3. Port busy? Use `docker-compose.verify-ports.yml` overlay (alt ports 13000/18000).
4. `docker compose logs backend --tail=100` for migration / DB URL errors.

## Auth / logout still allows API

Access JWTs are denylisted in Redis on logout when the client sends `access_token`. If Redis is down, denylist fails open (15m TTL bound) and increments `raginspector_jwt_denylist_failopen_total` — watch the Grafana alert `JwtDenylistFailOpen`.

## Metrics look empty

Hit a few API routes, then scrape `GET /api/v1/ops/metrics`. HTTP RED counters are process-local; Prometheus recording rules in `infra/observability/recording_rules.yml` aggregate across scrapes.

## MFA / SSO oddities

MFA is **login-gated** when a factor is enrolled. Google SSO needs `GOOGLE_OAUTH_*`. SAML/SCIM remain experimental — do not treat as GA.
