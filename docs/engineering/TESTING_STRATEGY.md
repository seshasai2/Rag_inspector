# Testing strategy

Layers of verification in RAGInspector.

## Pyramid

| Layer | Location | Runner | Scope |
|-------|----------|--------|-------|
| Unit | `backend/tests/unit/` | `make test-backend` | Services, gates, classifiers; heavy mocking |
| API integration | `backend/tests/test_api.py`, `tests/integration/` | pytest + httpx ASGI | Auth, ops, flows on SQLite/Postgres |
| SDK | `sdk/tests/` | `make test-sdk` | Client behavior |
| Frontend unit | `frontend` Vitest | `make test-frontend` | Components / hooks |
| E2E | `frontend/e2e` | Playwright (opt-in) | Auth, dashboard, nav |
| Load | `loadtests/` | k6 / Locust | Health readiness capacity |

## Backend conventions

- Set `TESTING=1` before imports (see `tests/conftest.py`) so SlowAPI disables.
- Prefer SQLite aiosqlite on Windows; Postgres in CI when available.
- Use `httpx.ASGITransport` + `AsyncClient` for ASGI tests.
- Integration tests skip gracefully when optional dependencies (live Redis) are down, or mock Redis.
- Do not require network LLM calls in unit tests.

## Frontend

- Vitest + Testing Library for component logic.
- Playwright for critical journeys; see `frontend/e2e/README.md` for scripts to add.

## What “done” means for a feature PR

1. Unit coverage for new service branches.
2. API test or integration for new endpoints.
3. Lint + typecheck clean.
4. Docs updated when contracts change (`docs/API.md` or architecture).

## Load / performance

Not every PR; run before releases or capacity changes. Capture summaries next to [PERFORMANCE_REPORT.md](../../PERFORMANCE_REPORT.md).

Related: [RELEASE_PROCESS.md](RELEASE_PROCESS.md), [CODING_STANDARDS.md](CODING_STANDARDS.md).
