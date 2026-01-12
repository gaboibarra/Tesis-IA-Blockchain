$ErrorActionPreference = "SilentlyContinue"
Get-Process python -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process node   -ErrorAction SilentlyContinue | Stop-Process -Force
Get-Process ganache* -ErrorAction SilentlyContinue | Stop-Process -Force
Write-Host "Procesos de demo detenidos."
