# Coding standards

Standards for RAGInspector backend (Python) and frontend (TypeScript/React). Tooling is the source of enforcement; this document explains intent.

## Python (backend)

| Tool | Command | Rule |
|------|---------|------|
| Ruff | `make lint-backend` | Lint; prefer fixing over ignoring |
| Black + isort | `make format-backend` | Format and import order |
| mypy | `make typecheck-backend` | Gradual typing on `app/` |
| pytest | `make test-backend` | Unit tests under `tests/unit/` |
| Bandit | `make security-bandit` | Basic SAST |

### Conventions

- Prefer explicit imports; no wildcard imports in application code.
- Domain errors inherit `BaseRAGInspectorError` with stable `code` values.
- Async SQLAlchemy sessions via `get_db`; do not leak sessions across tasks.
- Celery tasks stay thin: validate ids, call services, record job status.
- Secrets never logged; use structlog with bound `request_id`.
- IDs are `str` UUIDs (`String(36)`), not native UUID columns in new code.
- Pagination through `app/core/pagination.py` caps — do not invent ad-hoc limits.

## TypeScript (frontend)

| Tool | Command |
|------|---------|
| ESLint | `npm run lint` |
| `tsc --noEmit` | `npm run typecheck` |
| Vitest | `npm test` |

### Conventions

- App Router under `frontend/src/app`; shared UI in `components/`.
- Prefer existing data hooks / axios client patterns over parallel fetch stacks.
- Do not commit `.env` with secrets; use documented public env vars only.
- Keep grounding UI accessible: keyboard pin/hover equivalents where present.

## Git / PR hygiene

- Small PRs mapped to phase/checklist items when possible.
- Do not commit `node_modules`, `.venv`, local DB files, or API key material.
- Match existing module structure before inventing new top-level packages.

## Docstrings / comments

- Comment non-obvious invariants (e.g., ingest persists before enqueue).
- Skip narrating obvious code; prefer types and tests.

Related: [API_DESIGN.md](API_DESIGN.md), [TESTING_STRATEGY.md](TESTING_STRATEGY.md), [SECURITY.md](SECURITY.md).
