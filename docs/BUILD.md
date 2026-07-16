# Build, bootstrap & release

Clean-clone path for any engineer:

```bash
git clone <repo-url> raginspector
cd raginspector
cp .env.example .env          # set SECRET_KEY (≥32 chars)
make bootstrap                # build → start → migrate → health
```

Stack: http://localhost:8000 (API), http://localhost:3000 (UI).

## Make targets

| Target | Purpose |
|--------|---------|
| `make bootstrap` | One-command local bring-up |
| `make up` / `down` | Start / stop development compose |
| `make migrate` | Alembic upgrade head |
| `make test` / `lint` / `typecheck` | Local quality gates |
| `make up-test` | Ephemeral test compose |
| `make up-prod` | Production compose (needs `.env.production`) |
| `make up-obs` | Dev + Prometheus (9090) / Grafana (3001) |
| `make package-sdk` | Build + validate PyPI artifacts |
| `make check-versions` | SemVer sync across packages |
| `make release-check` | Local release gate |

## Environments

| Env | Compose / config |
|-----|------------------|
| Development | `docker-compose.yml` + `.env` |
| Testing | `docker-compose.test.yml` |
| Production | `docker-compose.prod.yml` + `.env.production` |
| Observability | overlay `docker-compose.observability.yml` |

Never reuse production secrets in development or testing.

## CI

Every PR runs `.github/workflows/ci.yml`:

lint/format → types → unit + integration tests → SDK package → frontend build → compose validate → Docker builds (BuildKit cache) → security scans (gitleaks, Trivy, pip-audit, npm audit) → version consistency → release validation gate.

Failures fail the pipeline immediately (job `needs` chain).

## Release

1. Bump `VERSION` and matching versions in `backend/pyproject.toml`, `frontend/package.json`, `sdk/pyproject.toml`, `sdk/raginspector/__init__.py`
2. Update `CHANGELOG.md` under `## [x.y.z]`
3. `make release-check`
4. Tag `vX.Y.Z` and push — `.github/workflows/release.yml` builds SDK wheels, container archives, and a GitHub Release

## Migration safety

- CI upgrades to head against Postgres.
- `scripts/check_migration_downgrades.py` requires every revision to define `downgrade()`.
- Prefer additive migrations; destructive changes need explicit review / confirmation in PRs.
- Production: `docker compose -f docker-compose.prod.yml --env-file .env.production run --rm backend alembic upgrade head`

- Backend / workers: multi-stage, venv, non-root `app` (uid 10001), `tini`, healthcheck `/live`, production config fail-fast
- Frontend: multi-stage, `npm ci`, Next standalone, non-root `nextjs`
- Model cache volume: `/app/.cache/huggingface`

## SDK (PyPI)

```bash
cd sdk && python -m build && twine check dist/*
# publish: twine upload dist/*
```

Metadata: `sdk/pyproject.toml` (PEP 621).
