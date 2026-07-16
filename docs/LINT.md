# Lint & typecheck (Phase 7.6)

CI blocks PRs when these fail (see `.github/workflows/ci.yml`).

## Backend

| Tool | Command | Scope |
|------|---------|--------|
| **Ruff** | `cd backend && python -m ruff check app` | Lint (`pyproject.toml`) |
| **Mypy** | `cd backend && python -m mypy` | Gradual: `app/core` + selected services |

```bash
make lint-backend
make typecheck-backend
```

SQLAlchemy `== True` / `!= None` comparisons are intentionally allowed (Ruff `E711`/`E712` ignored).

## Frontend

| Tool | Command |
|------|---------|
| **ESLint** | `cd frontend && npm run lint` (`next lint`) |
| **TypeScript** | `cd frontend && npm run typecheck` (`tsc --noEmit`) |

```bash
make lint-frontend
make typecheck-frontend
# or
make lint && make typecheck
```

## Dependencies

Dev pins live in `backend/requirements-dev.txt` (`ruff`, `mypy`). Regenerate from `requirements-dev.in` when bumping.
