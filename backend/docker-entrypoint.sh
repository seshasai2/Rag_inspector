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
  echo "SEED_DEMO_ON_START=1 — seeding demo dataset" >&2
  FORCE_FLAG=""
  if [ "${SEED_DEMO_FORCE:-0}" = "1" ]; then
    FORCE_FLAG="--force"
  fi
  python scripts/seed_demo.py ${FORCE_FLAG} || echo "demo seed failed (non-fatal)" >&2
fi

exec "$@"
