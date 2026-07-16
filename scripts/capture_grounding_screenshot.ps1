# Capture static grounding HTML → PNG (Phase 9.3).
param(
  [string]$Out = (Join-Path (Split-Path -Parent $PSScriptRoot) "docs\screenshots\grounding-attribution.png")
)
$ErrorActionPreference = "Stop"
$html = Join-Path (Split-Path -Parent $PSScriptRoot) "docs\screenshots\grounding-attribution.html"
$uri = ([Uri]$html).AbsoluteUri
npx --yes playwright install chromium
npx --yes playwright screenshot $uri $Out --viewport-size=1200,700
Write-Host "Wrote $Out"
