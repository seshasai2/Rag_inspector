#!/usr/bin/env bash
# Non-destructive restore test into raginspector_restore_test (Phase 8.5).
# Usage: ./scripts/restore_test.sh raginspector_YYYYMMDD_HHMMSS.sql.gz [prod]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
DUMP="${1:?dump filename required, e.g. raginspector_20260101_120000.sql.gz}"
COMPOSE=(docker compose)
if [[ "${2:-}" == "prod" ]]; then
  COMPOSE=(docker compose -f docker-compose.prod.yml --env-file .env.production)
fi
"${COMPOSE[@]}" exec postgres_backup test -f "/backups/$DUMP"
"${COMPOSE[@]}" exec db createdb -U raginspector raginspector_restore_test || true
"${COMPOSE[@]}" exec -T postgres_backup sh -c "gzip -dc /backups/$DUMP" \
  | "${COMPOSE[@]}" exec -T db psql -U raginspector -d raginspector_restore_test -v ON_ERROR_STOP=1
"${COMPOSE[@]}" exec db psql -U raginspector -d raginspector_restore_test -c '\dt'
"${COMPOSE[@]}" exec db dropdb -U raginspector raginspector_restore_test
echo "Restore test OK for $DUMP"
