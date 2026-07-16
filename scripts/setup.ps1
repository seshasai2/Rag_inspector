# RAGInspector Windows setup (PowerShell)
# Usage (from repo root):
#   Set-ExecutionPolicy -Scope Process Bypass
#   .\scripts\setup.ps1
#
# Requires: Docker Desktop with Compose v2

$ErrorActionPreference = "Stop"

Write-Host "RAGInspector Setup (Windows)" -ForegroundColor Cyan
Write-Host "============================"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "Docker is required. Install Docker Desktop: https://docs.docker.com/desktop/setup/install/windows-install/" -ForegroundColor Red
    exit 1
}

docker compose version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker Compose v2 is required (docker compose)." -ForegroundColor Red
    exit 1
}

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".env")) {
    Write-Host "Creating .env from .env.example..."
    Copy-Item ".env.example" ".env"
    $secret = -join ((1..48) | ForEach-Object { '{0:x}' -f (Get-Random -Max 16) })
    try {
        $secret = python -c "import secrets; print(secrets.token_urlsafe(48))"
    } catch {
        # keep hex fallback
    }
    $placeholder = "change-me-generate-a-32-plus-char-secret"
    $envText = Get-Content ".env" -Raw
    if ($envText -match [regex]::Escape($placeholder)) {
        $envText = $envText.Replace($placeholder, $secret)
        Set-Content -Path ".env" -Value $envText -NoNewline
        Write-Host ".env created with a generated SECRET_KEY."
    } else {
        Write-Host "SECRET_KEY placeholder not found — set SECRET_KEY in .env manually." -ForegroundColor Yellow
    }
} else {
    Write-Host ".env already exists."
}

Write-Host ""
Write-Host "Building Docker images..."
docker compose build
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Starting database and Redis..."
docker compose up -d db redis
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Waiting for database health..."
Start-Sleep -Seconds 8

Write-Host ""
Write-Host "Running migrations..."
docker compose run --rm backend alembic upgrade head
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Starting all services..."
docker compose up -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "RAGInspector is running!" -ForegroundColor Green
Write-Host ""
Write-Host "   Frontend:  http://localhost:3000"
Write-Host "   Backend:   http://localhost:8000"
Write-Host "   API Docs:  http://localhost:8000/docs"
Write-Host ""
Write-Host "Next steps:"
Write-Host "   1. Seed demo:  docker compose run --rm backend python scripts/seed_demo.py"
Write-Host "   2. Login:      demo@example.com / DemoPass123!"
Write-Host "   3. Docs:       docs\WINDOWS.md , docs\DEVELOPER.md"
Write-Host ""
