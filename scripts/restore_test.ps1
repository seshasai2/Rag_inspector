# Non-destructive restore test into raginspector_restore_test (Phase 8.5).
# Usage: .\scripts\restore_test.ps1 raginspector_YYYYMMDD_HHMMSS.sql.gz [-Prod]
param(
  [Parameter(Mandatory = $true)][string]$Dump,
  [switch]$Prod
)
$ErrorActionPreference = "Stop"
Set-Location (Split-Path -Parent $PSScriptRoot)
$compose = @("compose")
if ($Prod) {
  $compose = @("compose", "-f", "docker-compose.prod.yml", "--env-file", ".env.production")
}
& docker @compose exec postgres_backup test -f "/backups/$Dump"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& docker @compose exec db createdb -U raginspector raginspector_restore_test
& docker @compose exec -T postgres_backup sh -c "gzip -dc /backups/$Dump" |
  & docker @compose exec -T db psql -U raginspector -d raginspector_restore_test -v ON_ERROR_STOP=1
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
& docker @compose exec db psql -U raginspector -d raginspector_restore_test -c '\dt'
& docker @compose exec db dropdb -U raginspector raginspector_restore_test
Write-Host "Restore test OK for $Dump"
