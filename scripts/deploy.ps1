# RAGInspector production deploy (Docker Compose — free/self-hosted).
# Usage:
#   .\scripts\deploy.ps1
#   .\scripts\deploy.ps1 -Obs
#   .\scripts\deploy.ps1 -Validate

param(
    [switch]$Obs,
    [switch]$Validate
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

if (-not (Test-Path ".env.production")) {
    Write-Error "Missing .env.production — copy from .env.production.example and fill secrets."
}

# Load key env vars for validation (simple KEY=VALUE parser)
Get-Content ".env.production" | ForEach-Object {
    if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$') {
        $name = $Matches[1]
        $val = $Matches[2].Trim('"')
        [Environment]::SetEnvironmentVariable($name, $val, "Process")
    }
}

if (-not $env:SECRET_KEY -or $env:SECRET_KEY.Length -lt 32) {
    Write-Error "SECRET_KEY must be set (≥32 chars) in .env.production"
}
if (-not $env:OPS_SHARED_TOKEN -or $env:OPS_SHARED_TOKEN.Length -lt 16) {
    Write-Error "OPS_SHARED_TOKEN must be set (≥16 chars) in .env.production"
}

$ComposeArgs = @("-f", "docker-compose.prod.yml", "--env-file", ".env.production")

if ($Validate) {
    python scripts/validate_release.py
    exit $LASTEXITCODE
}

Write-Host "==> Validating compose"
docker compose @ComposeArgs config --quiet

Write-Host "==> Building and starting production stack"
docker compose @ComposeArgs up -d --build

if ($Obs) {
    Write-Host "==> Starting observability overlay"
    docker compose -f docker-compose.prod.yml -f docker-compose.observability.yml --env-file .env.production up -d
}

Write-Host "==> Waiting for backend /live"
$ok = $false
for ($i = 1; $i -le 60; $i++) {
    try {
        docker compose @ComposeArgs exec -T backend curl -fsS http://127.0.0.1:8000/live | Out-Null
        if ($LASTEXITCODE -eq 0) { $ok = $true; break }
    } catch { }
    Start-Sleep -Seconds 5
}
if (-not $ok) { Write-Error "Backend health timeout" }

Write-Host "==> Running migrations"
docker compose @ComposeArgs run --rm backend alembic upgrade head

Write-Host "==> Validating release endpoints"
try { python scripts/validate_release.py } catch { Write-Warning $_ }

$port = if ($env:HTTP_PORT) { $env:HTTP_PORT } else { "80" }
Write-Host ""
Write-Host "Deploy complete."
Write-Host "  API (via Nginx): http://localhost:$port"
Write-Host "  Frontend free hosting: see docs/DEPLOYMENT.md (Vercel / Cloudflare Pages)"
if ($Obs) {
    Write-Host "  Prometheus: http://localhost:9090"
    Write-Host "  Grafana:    http://localhost:3001"
}
