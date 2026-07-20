#!/bin/sh
# Backend / worker entrypoint — fail fast on invalid production config.
# Optional: RUN_MIGRATIONS=1 applies Alembic before the main command (web only).
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

exec "$@"
