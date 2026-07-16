# Contributing to RAGInspector

Thanks for helping. Goal: a new contributor can **clone → run → see the demo dashboard in under 30 minutes**.

Full walkthrough: **[docs/DEVELOPER.md](docs/DEVELOPER.md)**.

## Before you start

1. Read **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** (what is core vs deferred).
2. Follow **[docs/DEVELOPER.md](docs/DEVELOPER.md)** (prereqs, Docker path, seed login). On Windows, use **[docs/WINDOWS.md](docs/WINDOWS.md)** + `scripts/setup.ps1` then `scripts/bootstrap.ps1`.
3. Skim **[ROADMAP.md](ROADMAP.md)** — work one Immediate Next Task at a time; do not expand Phase 10 stubs. Troubleshooting: **[docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)**.

## Development workflow

```bash
# Preferred: Make targets (see Makefile)
make up && make migrate && make seed
make test
make lint
```

| Area | Command |
|------|---------|
| Backend unit tests | `cd backend && python -m pytest tests/unit/ -q` |
| Backend lint | `cd backend && python -m ruff check app` |
| Backend typecheck | `cd backend && python -m mypy` |
| Frontend tests | `cd frontend && npm test` |
| Frontend lint | `cd frontend && npm run lint` |
| Frontend typecheck | `cd frontend && npm run typecheck` |
| Compose validity | `docker compose config --quiet` |

Python **3.11** matches Docker/CI. Prefer `requirements-dev.txt` for local tests.

## Pull requests

- Keep PRs focused on one roadmap task or one bugfix.
- Do not commit `.env`, secrets, model weights, or `node_modules`.
- Include a short summary + how you verified (commands run).
- If you touch list APIs, keep pagination caps (`app/core/pagination.py`).
- If you touch analysis workers, note ML cold-start impact (`docs/COLD_START.md`, `docs/WORKER.md`).
- Mark experimental / unfinished UI honestly (`docs/EXPERIMENTAL.md`) — do not present stubs as live features.

## Code layout (where to put things)

| Change | Prefer |
|--------|--------|
| HTTP handlers | `backend/app/api/v1/endpoints/` (thin) |
| Business logic | `backend/app/services/` |
| ORM models | `backend/app/models/` |
| Celery tasks | `backend/app/workers/` |
| UI pages | `frontend/src/app/` |
| Shared UI | `frontend/src/components/` — prefer `components/ui/` (`StatCard`, `Panel`, tokens in `lib/design-tokens.ts`) |

## Security & secrets

- Copy `.env.example` → `.env`; never commit real keys.
- Production checklist: `docs/DEPLOYMENT.md`, `SECURITY.md`.

## Questions / scope

Primary product truth for hiring demos: `08_RAGInspector_PRD.md` (v1). Enterprise PRD v3 is Phase 10 only.
