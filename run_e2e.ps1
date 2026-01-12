param(
  [int]$Limit = 500,
  [string]$ScoreUrl = "http://127.0.0.1:5000/score"
)
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSCommandPath
Set-Location $repo
$venv = "$repo\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $venv)) { $venv = "$repo\.venv311\Scripts\Activate.ps1" }
. $venv

Write-Host "[E2E] limit=$Limit url=$ScoreUrl"
python .\scripts\run_e2e.py --limit $Limit --score-url $ScoreUrl

# Mostrar resumen clave del dashboard
$sum = Join-Path $repo "reports\e2e_summary.json"
if (Test-Path $sum) {
  $obj = Get-Content $sum | ConvertFrom-Json
  "{0,-18} {1}" -f "p95_scoring_ms:", [math]::Round($obj.p95_scoring_ms,1)
  "{0,-18} {1}" -f "p95_e2e_ms:",     [math]::Round($obj.p95_e2e_ms,1)
  "{0,-18} {1}%" -f "corr_secure→evt:", [math]::Round($obj.correlation_secure_to_event_pct,1)
} else {
  Write-Warning "No se encontró reports\e2e_summary.json"
}
