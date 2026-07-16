# Windows setup (PowerShell) — Phase 7.7

This guide is for **Windows 10/11 + PowerShell + Docker Desktop**. Prefer these commands over `bash scripts/setup.sh` and GNU `make` unless you already have them (Git Bash / WSL / Chocolatey make).

Full contributor flow: [DEVELOPER.md](DEVELOPER.md). Demo login: [SEED.md](SEED.md).

## Prerequisites

| Tool | Notes |
|------|--------|
| [Docker Desktop](https://docs.docker.com/desktop/setup/install/windows-install/) | Enable WSL2 backend if prompted; Compose v2 (`docker compose`) |
| [Git for Windows](https://git-scm.com/download/win) | Includes optional Git Bash |
| PowerShell 5.1+ or PowerShell 7 | Built-in Windows PowerShell is fine |
| Python 3.11 + Node 20 | Only for hybrid (host API / frontend) development |

Optional: [Make for Windows](https://community.chocolatey.org/packages/make) if you want `make up` — not required.

## Path A — One-shot setup script (~15–20 min)

From the repo root in PowerShell:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\setup.ps1
```

Then seed and open the UI:

```powershell
docker compose run --rm backend python scripts/seed_demo.py
Start-Process "http://localhost:3000"
```

**Demo login:** `demo@example.com` / `DemoPass123!`

### Equivalent commands (no script)

```powershell
Copy-Item .env.example .env
# Edit .env — set a long SECRET_KEY

docker compose up -d --build
docker compose run --rm backend alembic upgrade head
docker compose run --rm backend python scripts/seed_demo.py
docker compose ps
```

Health check without `curl` (Windows may lack curl on older hosts; Win10+ usually has it):

```powershell
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8000/api/v1/ops/ready
```

### Port conflicts (other apps already on 3000/5432/6379/8000)

Use the verification overlay so Compose still binds cleanly:

```powershell
docker compose -f docker-compose.yml -f docker-compose.verify-ports.yml up -d --build
# Then: API http://localhost:18000  UI http://localhost:13000  Nginx http://localhost:18080
# DB host 15432 · Redis host 16379
```

Run migrations **before** relying on the API schema (Postgres is Alembic-owned; do not expect auto `create_all`):

```powershell
docker compose -f docker-compose.yml -f docker-compose.verify-ports.yml run --rm backend alembic upgrade head
docker compose -f docker-compose.yml -f docker-compose.verify-ports.yml run --rm backend python scripts/seed_demo.py
```

For browser UI testing against these ports, set `NEXT_PUBLIC_API_URL=http://localhost:18000` in `.env` before rebuilding the frontend image.

## Path B — Hybrid: DB in Docker, API on the host

```powershell
docker compose up -d db redis

python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend\requirements-dev.txt

cd backend
alembic upgrade head
python scripts\seed_demo.py
uvicorn app.main:app --reload --port 8000
```

Frontend (second terminal):

```powershell
cd frontend
npm install --legacy-peer-deps
$env:NEXT_PUBLIC_API_URL = "http://localhost:8000"
npm run dev
```

Celery worker (optional; not needed for seeded completed traces):

```powershell
cd backend
.\.venv\Scripts\Activate.ps1   # if not already active
celery -A app.workers.celery_app worker --loglevel=info --concurrency=2 -Q analysis,celery
```

## Make targets without Make

| Make | PowerShell |
|------|------------|
| `make up` | `docker compose up -d --build` |
| `make down` | `docker compose down` |
| `make migrate` | `docker compose run --rm backend alembic upgrade head` |
| `make seed` | `docker compose run --rm backend python scripts/seed_demo.py` |
| `make test` | `cd backend; ..\.venv\Scripts\python.exe -m pytest tests\unit\ -q` then `cd frontend; npm test` |
| `make lint` | `cd backend; python -m ruff check app` then `cd frontend; npm run lint` |
| `make typecheck` | `cd backend; python -m mypy` then `cd frontend; npm run typecheck` |
| `make logs` | `docker compose logs -f --tail 100` |

## Common Windows issues

| Symptom | Fix |
|---------|-----|
| `scripts\setup.ps1` blocked | `Set-ExecutionPolicy -Scope Process Bypass` then re-run |
| Docker Desktop not running | Start Docker Desktop; wait until it says “Running” |
| Port 3000 / 8000 / 5432 in use | `netstat -ano \| findstr :8000` then stop the conflicting process, or change compose ports |
| Line endings / shell scripts fail | Use `setup.ps1` or `docker compose` — avoid relying on `setup.sh` in cmd.exe |
| `Activate.ps1` blocked | Same Process Bypass policy, or run `.venv\Scripts\activate.bat` from cmd |
| Slow first worker start | ML model download/warm — see [COLD_START.md](COLD_START.md); seeded demo does not need the worker |
| Path length / venv weirdness | Keep the repo under a short path (e.g. `C:\dev\raginspector`) |

## WSL2 alternative

If you prefer a Linux toolchain, clone inside WSL and follow [DEVELOPER.md](DEVELOPER.md) Path A with bash/`make`. Docker Desktop can share the WSL distro.

## Related

- [DEVELOPER.md](DEVELOPER.md) — cross-platform 30-minute guide  
- [COMPOSE_HEALTH.md](COMPOSE_HEALTH.md) — healthchecks  
- [LINT.md](LINT.md) — CI lint/typecheck  
- [CONTRIBUTING.md](../CONTRIBUTING.md) — PR workflow  
