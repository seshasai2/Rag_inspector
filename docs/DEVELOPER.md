# Developer guide (under 30 minutes)

Get RAGInspector running locally, log into the seeded demo, and know where docs live.

## Prerequisites (~5 min)

| Tool | Notes |
|------|--------|
| **Docker Desktop** (or Engine + Compose v2) | Required for Postgres, Redis, and the easy path |
| **Make** (optional) | `Makefile` targets; on Windows see [WINDOWS.md](WINDOWS.md) for PowerShell equivalents |
| **Git** | Clone the repo |
| **Python 3.11** + **Node 20+** | Only if you develop API/UI outside containers |
| **Windows** | Prefer [WINDOWS.md](WINDOWS.md) + `scripts/setup.ps1` instead of bash/`make` |

Billing (Razorpay) and Ollama are **optional** for browsing the seeded dashboard.

## Path A — Docker full stack (~15–20 min)

```bash
git clone <repo-url> raginspector
cd raginspector
cp .env.example .env
# Optional: set a strong SECRET_KEY in .env

docker compose up -d --build
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python scripts/seed_demo.py
```

Or with Make:

```bash
cp .env.example .env
make up
make migrate
make seed
```

| URL | Purpose |
|-----|---------|
| http://localhost:3000 | Frontend |
| http://localhost:8000/docs | OpenAPI |
| http://localhost:8000/api/v1/ops/ready | Readiness (DB + Redis) |
| http://localhost:8000/health | Process liveness |

**Demo login** (see [SEED.md](SEED.md)):

- Email: `demo@example.com`
- Password: `DemoPass123!`

You should see dashboard metrics, queries (including a hallucination example), and chunks — **no real RAG app required**.

### Health / startup order

Compose waits on healthy `db` / `redis` before backend; frontend waits on a healthy backend. Details: [COMPOSE_HEALTH.md](COMPOSE_HEALTH.md).

```bash
docker compose ps
curl -fsS http://localhost:8000/api/v1/ops/ready
```

## Path B — Hybrid (API on host, DB in Docker) (~20–25 min)

Useful when iterating on FastAPI with hot reload.

```bash
docker compose up -d db redis

cd backend
python -m venv ../.venv          # or use existing repo .venv
# Windows: ..\.venv\Scripts\activate
# Unix:    source ../.venv/bin/activate
pip install -r requirements-dev.txt

# Point .env / environment at localhost Postgres + Redis (see .env.example)
alembic upgrade head
python scripts/seed_demo.py
uvicorn app.main:app --reload --port 8000
```

In another terminal (optional, for *new* ingest analysis — not needed for seeded data):

```bash
cd backend
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 -Q analysis,celery
```

Frontend:

```bash
cd frontend
npm install --legacy-peer-deps
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

## Verify you are done (<5 min)

- [ ] `GET /health` → `healthy`
- [ ] `GET /api/v1/ops/ready` → HTTP 200 / `"status":"ready"`
- [ ] Login with demo credentials
- [ ] Dashboard shows non-zero queries / hallucination rate
- [ ] Open a query detail and see grounding sentences
- [ ] (Optional) `cd backend && python -m pytest tests/unit/ -q` passes

## Common issues

| Symptom | Fix |
|---------|-----|
| Backend never healthy | `docker compose logs backend`; check `SECRET_KEY` / DB URL; wait for `start_period` |
| Frontend 502 / blank API | Backend not ready; confirm `NEXT_PUBLIC_API_URL` |
| Login blocked (email verification) | Seeded demo user is verified; for new signups in prod see `REQUIRE_EMAIL_VERIFICATION` in [DEPLOYMENT.md](DEPLOYMENT.md) |
| Traces stuck `pending` | Start `celery_worker` or use seeded completed traces; see [WORKER.md](WORKER.md) |
| OOM on worker | Keep `--concurrency` at 1–2; see [COLD_START.md](COLD_START.md) |
| Windows + Make missing | Use [WINDOWS.md](WINDOWS.md) / `scripts/setup.ps1` — do not require GNU make |

## Day-to-day commands

See root `Makefile`: `up`, `down`, `migrate`, `seed`, `test`, `lint`, `logs`, `ps`.

Contribution norms and PR expectations: [CONTRIBUTING.md](../CONTRIBUTING.md).

## Doc map

| Doc | When |
|-----|------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | What to build / what is deferred |
| [SEED.md](SEED.md) | Demo dataset |
| [COMPOSE_HEALTH.md](COMPOSE_HEALTH.md) | Healthchecks / depends_on |
| [WORKER.md](WORKER.md) | Celery concurrency + backlog metrics |
| [COLD_START.md](COLD_START.md) | ML model load / warm |
| [DASHBOARD_CACHE.md](DASHBOARD_CACHE.md) | Redis TTL for metrics |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production checklist |
| [EXPERIMENTAL.md](EXPERIMENTAL.md) | Stub / enterprise surfaces |
| [WINDOWS.md](WINDOWS.md) | PowerShell setup (no bash/make required) |
| [LINT.md](LINT.md) | Ruff / Mypy / ESLint / tsc CI gates |
| `ROADMAP.md` | Ordered engineering tasks |

## Scope reminder

Follow [ROADMAP.md](../ROADMAP.md). Phases 1–10 are complete; do not invent Phase 11 without a roadmap revision. Partial surfaces stay listed in [EXPERIMENTAL.md](EXPERIMENTAL.md).
