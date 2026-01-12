$ErrorActionPreference = "Stop"
$host.UI.RawUI.WindowTitle = "Ganache 8545"
if (-not (Get-Command ganache -ErrorAction SilentlyContinue)) {
  Write-Error "No encuentro 'ganache' en PATH. Abrí Ganache GUI o instala ganache-cli."
}
Start-Process powershell -ArgumentList @(
  "-NoExit","-Command","ganache -p 8545"
) | Out-Null

# Espera rápida de salud
Start-Sleep -Seconds 2
try {
  $resp = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:8545" -Method POST -Body '{"jsonrpc":"2.0","method":"web3_clientVersion","params":[],"id":1}'
  Write-Host "RPC OK en :8545"
} catch { Write-Warning "Aún no responde; dale 2-3s más." }
