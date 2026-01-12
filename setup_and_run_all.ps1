<#-----------------------------------------------------------------------------
  setup_and_run_all.ps1 – FraudChain Demo Launcher (Windows-only)

  Qué hace:
   1) Habilita política temporal para scripts y arranca transcript.
   2) Detecta Python 3.13 (fallback 3.11), crea/usa venv, instala requirements.
   3) Instala deps de Hardhat y compila.
   4) Verifica .env y creditcard.csv (opcional: setea THRESHOLD_OVERRIDE).
   5) Lanza Ganache, despliega contrato (autocompleta CONTRACT_ADDRESS).
   6) Lanza API Flask y Dashboard en ventanas separadas con health-checks.
   7) Corre simulación E2E (limit configurable) y deja reports\e2e_summary.json.
   8) Abre el dashboard en el navegador.

  Uso rápido:
    Set-ExecutionPolicy -Scope Process Bypass
    .\setup_and_run_all.ps1 -Limit 500 -ThresholdOverride 0.90

  Parámetros:
    -Limit               → filas para runner (default 500)
    -RPCPort             → 8545 por default
    -FlaskPort           → 5000 por default
    -DashPort            → 8050 por default
    -ThresholdOverride   → si se pasa, se escribe en .env (solo demo)
    -ForceRecompile      → recompila Hardhat aunque existan artefactos
    -SkipE2E             → lanza todo pero NO corre el runner

  Requisitos previos (1a vez por PC):
    - Python 3.13 o 3.11 x64 disponible en "py -0p"
    - Node.js 18+ (node, npm)
    - Ganache (CLI o GUI) en PATH (o abre GUI manual si preferís)
-----------------------------------------------------------------------------#>

param(
  [int]$Limit = 500,
  [int]$RPCPort = 8545,
  [int]$FlaskPort = 5000,
  [int]$DashPort = 8050,
  [double]$ThresholdOverride = [double]::NaN,
  [switch]$ForceRecompile = $false,
  [switch]$SkipE2E = $false
)

$ErrorActionPreference = "Stop"

function Sec($t){ Write-Host "`n=== $t ===" -ForegroundColor Cyan }
function Ok($t){ Write-Host "✔ $t" -ForegroundColor Green }
function Warn($t){ Write-Warning $t }
function Die($t){ throw $t }

function Ensure-Policy {
  Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force
  Start-Transcript -Path .\demo_full_log.txt -Append | Out-Null
  Sec "Policy + Transcript"
  Ok "ExecutionPolicy(Process)=Bypass, transcript on demo_full_log.txt"
}

function Assert-Cmd($name){
  if (-not (Get-Command $name -ErrorAction SilentlyContinue)){
    Die "No encuentro '$name' en PATH."
  }
}

function Get-PyCmd {
  $list = & py -0p | Out-String
  if ($list -match '3\.13'){ return 'py -3.13' }
  elseif ($list -match '3\.11'){ return 'py -3.11' }
  else { Die "No encontré Python 3.13 ni 3.11. Instálalo y reintenta." }
}

function Ensure-Venv {
  Sec "Virtualenv + requirements"
  $global:REPO = (Get-Location).Path
  $py = Get-PyCmd
  $venv = Join-Path $REPO ".venv"
  if (-not (Test-Path $venv)) {
    & $py -m venv $venv
    Ok "Venv creado en .venv"
  } else { Ok "Venv existente en .venv" }
  $global:ACT = Join-Path $venv "Scripts\Activate.ps1"
  if (-not (Test-Path $ACT)){ Die "No se encuentra Activate.ps1 en el venv." }
  . $ACT
  python -m pip install --upgrade pip
  if (-not (Test-Path ".\requirements.txt")){ Die "No encuentro requirements.txt en la raíz." }
  pip install --no-cache-dir -r .\requirements.txt
  Ok "requirements instalados"
}

function Ensure-Hardhat {
  Sec "Hardhat deps + compile"
  Push-Location .\hardhat
  if ($ForceRecompile -or -not (Test-Path ".\node_modules")) {
    Assert-Cmd npm; Assert-Cmd node
    npm ci
  }
  npx hardhat compile
  Pop-Location
  Ok "Hardhat listo"
}

function Ensure-Env-And-Data {
  Sec ".env + datos"
  if (-not (Test-Path ".\.env")) {
    if (Test-Path ".\.env.example"){ Copy-Item .\.env.example .\.env -Force; Warn "Se creó .env desde .env.example. Completa PRIVATE_KEY (Ganache)." }
    else { Warn "No existe .env ni .env.example. Crealo con RPC_URL, CHAIN_ID, PRIVATE_KEY, CONTRACT_ADDRESS." }
  }
  # Asegurar RPC_URL y CHAIN_ID
  $envPath = ".\.env"
  if (Test-Path $envPath) {
    $txt = Get-Content $envPath -Raw
    if ($txt -notmatch "RPC_URL="){
      Add-Content $envPath "`nRPC_URL=http://127.0.0.1:$RPCPort"
      Ok "RPC_URL agregado a .env"
    }
    if ($txt -notmatch "CHAIN_ID="){
      Add-Content $envPath "`nCHAIN_ID=1337"
      Ok "CHAIN_ID agregado a .env"
    }
    if (-not [double]::IsNaN($ThresholdOverride)) {
      $txt = Get-Content $envPath -Raw
      if ($txt -match "THRESHOLD_OVERRIDE="){
        (Get-Content $envPath) -replace 'THRESHOLD_OVERRIDE=.*', "THRESHOLD_OVERRIDE=$ThresholdOverride" | Set-Content $envPath -Encoding UTF8
        Ok "THRESHOLD_OVERRIDE actualizado a $ThresholdOverride"
      } else {
        Add-Content $envPath "`nTHRESHOLD_OVERRIDE=$ThresholdOverride"
        Ok "THRESHOLD_OVERRIDE=$ThresholdOverride agregado a .env"
      }
    }
  }
  if (-not (Test-Path ".\data\creditcard.csv")) {
    Warn "Falta data\creditcard.csv (el proyecto corre igual, pero entrenar/runner lo usan)."
  } else { Ok "OK datos: data\creditcard.csv" }
}

function Start-Ganache {
  Sec "Iniciar Ganache"
  Assert-Cmd ganache
  Start-Process powershell -ArgumentList @(
    "-NoExit","-Command","ganache -p $RPCPort"
  ) | Out-Null
  Start-Sleep -Seconds 2
  try {
    $payload = '{"jsonrpc":"2.0","method":"web3_clientVersion","params":[],"id":1}'
    Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$RPCPort" -Method POST -Body $payload | Out-Null
    Ok "RPC responde en :$RPCPort"
  } catch { Warn "Ganache aún inicializando… (OK)."; Start-Sleep -Seconds 3 }
}

function Deploy-Contract {
  Sec "Deploy contrato (autocompleta .env)"
  Push-Location .\hardhat
  $out = npx hardhat run .\scripts\deploy.js --network localhost
  Pop-Location
  $addrFile = ".\abi\TxRegistry.address"
  if (-not (Test-Path $addrFile)){ Die "No se generó abi\TxRegistry.address" }
  $addr = (Get-Content $addrFile -Raw).Trim()
  Ok "Contrato: $addr"
}

function Start-API {
  Sec "Lanzar API Flask"
  $env:PYTHONPATH = $REPO
  Start-Process powershell -ArgumentList @(
    "-NoExit","-Command","Set-Location `"$REPO`"; . `"$ACT`"; `$env:PYTHONPATH=`"$REPO`"; python -m api.app --port $FlaskPort"
  ) | Out-Null
  Start-Sleep -Seconds 2
  try {
    $resp = Invoke-WebRequest -UseBasicParsing -Uri "http://127.0.0.1:$FlaskPort/health" -Method GET
    if ($resp.StatusCode -eq 200){ Ok "API healthy en :$FlaskPort" }
  } catch { Warn "API arrancando… (si falla, revisa la ventana de la API)" }
}

function Start-Dashboard {
  Sec "Lanzar Dashboard"
  Start-Process powershell -ArgumentList @(
    "-NoExit","-Command","Set-Location `"$REPO`"; . `"$ACT`"; python .\dashboard\app.py --port $DashPort"
  ) | Out-Null
  Start-Sleep -Seconds 2
  Ok "Dashboard en http://127.0.0.1:$DashPort"
  try {
    Start-Process "http://127.0.0.1:$DashPort" | Out-Null
  } catch { }
}

function Smoke-Imports {
  Sec "Smoke imports (Flask/Web3/Dash/SciPy)"
  $env:PYTHONPATH = $REPO
  $code = @"
import sys
mods = 'flask,web3,dash,plotly,joblib,sklearn,pandas,numpy'.split(',')
bad=[]
for m in mods:
    try: __import__(m)
    except Exception as e: bad.append((m,str(e)))
if bad: 
    print('Fallo import en:',bad); sys.exit(1)
print('Imports OK')
"@
  python - << $code
  Ok "Imports OK"
}

function Run-E2E {
  Sec "Simulación E2E"
  if ($SkipE2E){ Warn "SkipE2E activado. No se corre el runner."; return }
  . $ACT
  $url = "http://127.0.0.1:$FlaskPort/score"
  python .\scripts\run_e2e.py --limit $Limit --score-url $url
  $sum = ".\reports\e2e_summary.json"
  if (Test-Path $sum){
    $obj = Get-Content $sum | ConvertFrom-Json
    "{0,-18} {1}" -f "p95_scoring_ms:", [math]::Round($obj.p95_scoring_ms,1) | Write-Host
    "{0,-18} {1}" -f "p95_e2e_ms:",     [math]::Round($obj.p95_e2e_ms,1)   | Write-Host
    "{0,-18} {1}%" -f "corr_secure→evt:", [math]::Round($obj.correlation_secure_to_event_pct,1) | Write-Host
    Ok "Resumen E2E escrito en reports\e2e_summary.json (ver Dashboard → Refresh)"
  } else { Warn "No se encontró reports\e2e_summary.json (ver logs del runner)." }
}

# =============== MAIN ===============
Ensure-Policy

Sec "Herramientas"
Assert-Cmd py; Assert-Cmd node; Assert-Cmd npm
Write-Host ("Python launcher: " + (& py -V))
Write-Host ("Node: " + (& node -v))
Write-Host ("npm:  " + (& npm -v))

Ensure-Venv
Smoke-Imports
Ensure-Hardhat
Ensure-Env-And-Data
Start-Ganache
Deploy-Contract
Start-API
Start-Dashboard
Run-E2E

Sec "Todo arriba ✅"
Write-Host "Dashboard:  http://127.0.0.1:$DashPort"
Write-Host "API (health): http://127.0.0.1:$FlaskPort/health"
Write-Host "Si querés cerrar rápido: crea un stop_all.ps1 que mate python/node/ganache."
Stop-Transcript | Out-Null
