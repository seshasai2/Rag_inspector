#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="${1:-$ROOT/docs/screenshots/grounding-attribution.png}"
HTML="$ROOT/docs/screenshots/grounding-attribution.html"
npx --yes playwright install chromium
npx --yes playwright screenshot "file://$HTML" "$OUT" --viewport-size=1200,700
echo "Wrote $OUT"
