#!/bin/sh
# Celery analysis worker for cloud / Compose overrides.
set -eu

CONCURRENCY="${CELERY_CONCURRENCY:-1}"
QUEUES="${CELERY_QUEUES:-analysis,celery}"

exec celery -A app.workers.celery_app worker \
  --loglevel="${CELERY_LOGLEVEL:-info}" \
  --concurrency="$CONCURRENCY" \
  -Q "$QUEUES"
