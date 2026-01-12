$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSCommandPath  # carpeta del script = raíz del repo
Set-Location $repo
$venv = "$repo\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $venv)) { $venv = "$repo\.venv311\Scripts\Activate.ps1" }
. $venv

$env:PYTHONPATH = $repo
$host.UI.RawUI.WindowTitle = "API Flask (5000)"
if (-not (Test-Path "$repo\.env")) { Write-Error ".env no existe. Copiá .env.example y completa PRIVATE_KEY / RPC_URL." }

Start-Process powershell -ArgumentList @(
  "-NoExit","-Command","Set-Location $repo; . $venv; `$env:PYTHONPATH='$repo'; python -m api.app"
) | Out-Null
