#!/usr/bin/env bash
# Generate self-signed certs for local HTTPS smoke tests (Phase 8.2).
# Usage: ./scripts/gen-dev-certs.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CERT_DIR="${TLS_CERTS_DIR:-$ROOT/certs}"
mkdir -p "$CERT_DIR"
docker run --rm -v "$CERT_DIR:/certs" alpine/openssl \
  req -x509 -nodes -newkey rsa:2048 -days 365 \
  -keyout /certs/privkey.pem \
  -out /certs/fullchain.pem \
  -subj "/CN=${TLS_CN:-localhost}"
echo "Wrote $CERT_DIR/fullchain.pem and privkey.pem"
echo "Next: docs/TLS.md (Path A)"
