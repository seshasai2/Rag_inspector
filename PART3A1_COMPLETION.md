# Part 3A.1 — Enterprise CI/CD, Docker, Build & Release

Status: **Complete**

## One-command path

```bash
cp .env.example .env   # set SECRET_KEY
make bootstrap         # build → up → migrate → health
```

Documented in `docs/BUILD.md` and README quick start.

## Delivered

| Area | What changed |
|------|----------------|
| CI | `.github/workflows/ci.yml` — parallel jobs, fail-fast `needs`, caches, artifacts, Black/isort/ruff/mypy/bandit, pytest+coverage, SDK build+twine, frontend lint/tsc/test/build, compose validate (dev/test/prod/obs), Docker Buildx+GHA cache, gitleaks/Trivy/pip-audit/npm audit, version consistency, release gate |
| Release | `.github/workflows/release.yml` — SemVer tag validation, SDK wheels, image archives, CHANGELOG notes, GitHub Release assets |
| Backend Docker | Multi-stage venv, pinned `python:3.11.12-slim-bookworm`, non-root uid 10001, `tini`, `/live` healthcheck, production fail-fast entrypoint |
| Frontend Docker | `npm ci`, standalone runner, non-root `nextjs`, healthcheck, security headers via Next config |
| Compose | `docker-compose.test.yml`, `docker-compose.observability.yml` + Prometheus/Grafana provisioning; HF cache path → `/app/.cache/huggingface` |
| SDK | `sdk/pyproject.toml` (PEP 621), `py.typed`, thin `setup.py`; `python -m build` + twine check **PASSED** |
| Versioning | Root `VERSION` + `scripts/check_versions.py` + `CHANGELOG.md` |
| Make | `bootstrap`, `up-test`, `up-obs`, `package-sdk`, `check-versions`, `release-check`, `format-backend` |
| Format | Backend app Black + isort applied (CI gate) |

## Validation executed locally

- `scripts/check_versions.py` — OK (1.0.0)
- `docker compose` / test / observability `config` — OK
- Backend unit tests — **253 passed**
- Black/isort/ruff check — pass
- SDK `build` + `twine check` — pass
- Bandit — no medium/high findings at `-ll -ii`

## Operator notes

- Full Docker image builds are heavy (CPU torch); CI builds them with Buildx layer cache.
- Observability metrics scrape `/api/v1/ops/metrics` (open when `OPS_SHARED_TOKEN` unset).
- After editing `requirements-dev.in` (bandit/black/isort), regenerate `requirements-dev.txt` when convenient; CI also `pip install`s those tools explicitly.
- Tag releases only after bumping `VERSION` + package versions + CHANGELOG section.

## Deferred (out of scope / intentional)

- Automatic PyPI upload (manual `twine upload` or add trusted publisher when ready)
- Container registry push (artifact archives on GitHub Release for now)
- Full Alembic downgrade guarantee for every historical migration (forward upgrades validated in CI; every revision defines `downgrade()`)

Do **not** proceed past Part 3A.1 until the above checklist is accepted.
