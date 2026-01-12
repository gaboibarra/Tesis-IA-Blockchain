$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent $PSCommandPath
Set-Location $repo
$venv = "$repo\.venv\Scripts\Activate.ps1"
if (-not (Test-Path $venv)) { $venv = "$repo\.venv311\Scripts\Activate.ps1" }
. $venv

$host.UI.RawUI.WindowTitle = "Dashboard (8050)"
Start-Process powershell -ArgumentList @(
  "-NoExit","-Command","Set-Location $repo; . $venv; python .\dashboard\app.py"
) | Out-Null

Start-Sleep -Seconds 1
Write-Host "Abrí http://127.0.0.1:8050"
