# RAGInspector Windows bootstrap (PowerShell twin of `make bootstrap`)
# Usage (from repo root):
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\scripts\bootstrap.ps1
#
# Requires: Docker Desktop with Compose v2, .env present (or run setup.ps1 first)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "==> Checking environment" -ForegroundColor Cyan
if (-not (Test-Path ".env")) {
    Write-Host "Missing .env — copying from .env.example" -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "Edit .env and set SECRET_KEY (>=32 chars), then re-run .\scripts\bootstrap.ps1" -ForegroundColor Red
    exit 1
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker is required. Install Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host "==> Validating compose"
docker compose config --quiet
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Building and starting stack"
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Waiting for backend health"
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
    docker compose exec -T backend curl -fsS http://127.0.0.1:8000/live 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) { $ok = $true; break }
    Start-Sleep -Seconds 5
}
if (-not $ok) {
    Write-Host "Backend health timeout" -ForegroundColor Red
    exit 1
}

Write-Host "==> Running migrations"
docker compose run --rm backend alembic upgrade head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "==> Ready — API http://localhost:8000  UI http://localhost:3000" -ForegroundColor Green
Write-Host "Optional: make seed  (or docker compose exec backend python scripts/seed_demo.py)"
