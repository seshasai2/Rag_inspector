#!/bin/sh
# Backend / worker entrypoint — fail fast on invalid production config.
set -eu

if [ "${ENVIRONMENT:-development}" = "production" ]; then
  python - <<'PY'
from app.core.config import validate_production_settings
validate_production_settings()
print("production settings validated", flush=True)
PY
fi

exec "$@"
