# List dumps from the postgres_backup volume (Phase 8.5).
# Usage: .\scripts\list_backups.ps1 [-Prod]
param([switch]$Prod)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
if ($Prod) {
  docker compose -f docker-compose.prod.yml --env-file .env.production exec postgres_backup ls -lah /backups
} else {
  docker compose exec postgres_backup ls -lah /backups
}
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
