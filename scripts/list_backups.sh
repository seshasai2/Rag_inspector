#!/usr/bin/env bash
# List dumps from the postgres_backup volume (Phase 8.5).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
COMPOSE=(docker compose)
if [[ "${1:-}" == "prod" ]]; then
  COMPOSE=(docker compose -f docker-compose.prod.yml --env-file .env.production)
fi
"${COMPOSE[@]}" exec postgres_backup ls -lah /backups
