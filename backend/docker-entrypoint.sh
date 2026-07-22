#!/bin/sh
# Backend / worker entrypoint — fail fast on invalid production config.
# Optional: RUN_MIGRATIONS=1 applies Alembic before the main command (web only).
# Optional: SEED_DEMO_ON_START=1 loads interview demo dataset after migrations.
set -eu

if [ "${ENVIRONMENT:-development}" = "production" ]; then
  python - <<'PY'
from app.core.config import validate_production_settings
validate_production_settings()
print("production settings validated", flush=True)
PY
fi

if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
  echo "RUN_MIGRATIONS=1 — applying Alembic migrations" >&2
  alembic upgrade head
fi

if [ "${SEED_DEMO_ON_START:-0}" = "1" ]; then
  # Idempotent only. Never --force on boot: wiping/reseeding before uvicorn binds
  # delays health checks on Render Free and causes 502 restart loops.
  # Intentional refresh: POST /api/v1/ops/seed-demo?force=true
  echo "SEED_DEMO_ON_START=1 — seeding demo dataset (idempotent)" >&2
  python scripts/seed_demo.py || echo "demo seed failed (non-fatal)" >&2
fi

exec "$@"
