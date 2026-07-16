#!/usr/bin/env bash
# Run unit tests with the Phase 4.5 critical-module coverage gate (≥95%).
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pytest tests/unit/ \
  --cov=app.services \
  --cov=app.workers \
  --cov-config=.coveragerc \
  --cov-report=term-missing:skip-covered \
  -q --tb=line
