#!/bin/sh
# Celery beat scheduler (single replica only).
set -eu

exec celery -A app.workers.celery_app beat --loglevel="${CELERY_LOGLEVEL:-info}"
