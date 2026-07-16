# Generate self-signed certs for local HTTPS smoke tests (Phase 8.2).
# Usage: .\scripts\gen-dev-certs.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$certDir = if ($env:TLS_CERTS_DIR) { $env:TLS_CERTS_DIR } else { Join-Path $root "certs" }
$cn = if ($env:TLS_CN) { $env:TLS_CN } else { "localhost" }
New-Item -ItemType Directory -Force -Path $certDir | Out-Null
$mount = "${certDir}:/certs"
docker run --rm -v $mount alpine/openssl `
  req -x509 -nodes -newkey rsa:2048 -days 365 `
  -keyout /certs/privkey.pem `
  -out /certs/fullchain.pem `
  -subj "/CN=$cn"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "Wrote $certDir\fullchain.pem and privkey.pem"
Write-Host "Next: docs\TLS.md (Path A)"
