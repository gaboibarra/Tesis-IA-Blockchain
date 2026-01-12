$ErrorActionPreference = "Stop"
& "$PSScriptRoot\start_ganache.ps1"
Start-Sleep -Seconds 2
& "$PSScriptRoot\start_api.ps1"
Start-Sleep -Seconds 2
& "$PSScriptRoot\start_dashboard.ps1"
Write-Host "Todo arriba. Si querés generar eventos: .\run_e2e.ps1 -Limit 500"
