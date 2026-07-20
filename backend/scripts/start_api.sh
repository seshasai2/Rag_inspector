#!/bin/sh
# Cloud / Docker API start command.
# Honors PORT (Render, Railway, Fly). Migrations: set RUN_MIGRATIONS=1 on the entrypoint.
set -eu

PORT="${PORT:-8000}"
WORKERS="${UVICORN_WORKERS:-1}"

exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers "$WORKERS"
