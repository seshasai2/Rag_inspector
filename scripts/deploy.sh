#!/usr/bin/env bash
# RAGInspector production deploy (Docker Compose — free/self-hosted).
# Usage:
#   ./scripts/deploy.sh              # build + up + migrate + health
#   ./scripts/deploy.sh --obs        # also start Prometheus/Grafana
#   ./scripts/deploy.sh --validate   # health checks only
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMPOSE=(docker compose -f docker-compose.prod.yml --env-file .env.production)
WITH_OBS=0
VALIDATE_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --obs) WITH_OBS=1 ;;
    --validate) VALIDATE_ONLY=1 ;;
    -h|--help)
      echo "Usage: $0 [--obs] [--validate]"
      exit 0
      ;;
  esac
done

if [[ ! -f .env.production ]]; then
  echo "Missing .env.production — copy from .env.production.example and fill secrets."
  exit 1
fi

# shellcheck disable=SC1091
set -a
# shellcheck disable=SC1090
source .env.production
set +a

if [[ -z "${SECRET_KEY:-}" || ${#SECRET_KEY} -lt 32 ]]; then
  echo "SECRET_KEY must be set (≥32 chars) in .env.production"
  exit 1
fi
if [[ -z "${OPS_SHARED_TOKEN:-}" || ${#OPS_SHARED_TOKEN} -lt 16 ]]; then
  echo "OPS_SHARED_TOKEN must be set (≥16 chars) in .env.production"
  exit 1
fi

if [[ "$VALIDATE_ONLY" -eq 1 ]]; then
  python scripts/validate_release.py
  exit $?
fi

echo "==> Validating compose"
"${COMPOSE[@]}" config --quiet

echo "==> Building and starting production stack"
"${COMPOSE[@]}" up -d --build

if [[ "$WITH_OBS" -eq 1 ]]; then
  echo "==> Starting observability overlay"
  docker compose -f docker-compose.prod.yml -f docker-compose.observability.yml \
    --env-file .env.production up -d
fi

echo "==> Waiting for backend /live"
for i in $(seq 1 60); do
  if "${COMPOSE[@]}" exec -T backend curl -fsS http://127.0.0.1:8000/live >/dev/null 2>&1; then
    break
  fi
  if [[ "$i" -eq 60 ]]; then
    echo "Backend health timeout"
    exit 1
  fi
  sleep 5
done

echo "==> Running migrations"
"${COMPOSE[@]}" run --rm backend alembic upgrade head

echo "==> Validating release endpoints"
python scripts/validate_release.py || true

echo ""
echo "Deploy complete."
echo "  API (via Nginx): http://localhost:${HTTP_PORT:-80}"
echo "  Direct backend:  check compose ports / nginx"
echo "  Frontend free hosting: see docs/DEPLOYMENT.md (Vercel / Cloudflare Pages)"
if [[ "$WITH_OBS" -eq 1 ]]; then
  echo "  Prometheus: http://localhost:9090"
  echo "  Grafana:    http://localhost:3001"
fi
