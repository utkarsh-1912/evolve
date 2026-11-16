# run_local.ps1 - no-Docker launcher for the evolve demo (R-DEMO-1). SIMULATED, synthetic data only.
# Starts the backend (uvicorn), citizen (:3000), counselor (:3001) and eval dashboard (:3002) dev servers,
# waits for health, then runs reset_demo.ps1 (reset + V3 pre-stage + partner IDs + counselor login + URLs).
# It never installs anything: missing dependencies are reported. ASCII-only (PowerShell 5.1 + no BOM).
#
#   powershell -ExecutionPolicy Bypass -File scripts\demo\run_local.ps1          # everything, live backend
#   ... run_local.ps1 -Mock      # OFFLINE: web apps on their built-in SIMULATED mock adapters, no backend
#                                # (eval dashboard still shows the evidence pack; its live feed reads "paused")
#   ... run_local.ps1 -NoWeb     # backend only
#   ... run_local.ps1 -Stop      # stop everything this script started
# Web ports are fixed (3000/3001/3002): the backend CORS allow-list names exactly those (DECISIONS #38).
param(
    [int]$ApiPort = 8000,
    [switch]$Mock,
    [switch]$NoWeb,
    [switch]$Stop
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$PidFile = Join-Path $env:TEMP "evolve-demo-pids.txt"
$LogDir = Join-Path $env:TEMP "evolve-demo-logs"

function Stop-Demo {
    if (-not (Test-Path $PidFile)) { Write-Host "Nothing to stop (no $PidFile)."; return }
    foreach ($line in Get-Content $PidFile) {
        if (-not $line) { continue }
        # taskkill /T also stops the node/python children that npm and uvicorn spawn.
        & taskkill.exe /PID ([int]$line) /T /F 2>$null | Out-Null
        Write-Host "stopped pid $line"
    }
    Remove-Item $PidFile -Force
}
if ($Stop) { Stop-Demo; exit 0 }

function Wait-Url([string]$url, [int]$seconds) {
    $deadline = (Get-Date).AddSeconds($seconds)
    while ((Get-Date) -lt $deadline) {
        try { Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 60 | Out-Null; return $true }
        catch { if ($_.Exception.Response) { return $true }; Start-Sleep -Seconds 2 }
    }
    return $false
}
function Test-PortFree([int]$port) {
    $l = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    return -not $l
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
if (Test-Path $PidFile) { Write-Host "A previous run is recorded in $PidFile - stopping it first."; Stop-Demo }
$pids = @()
$api = "http://localhost:$ApiPort"
$apps = @(
    @{ name = "citizen";   dir = "apps\citizen";        port = 3000 },
    @{ name = "counselor"; dir = "apps\counselor";      port = 3001 },
    @{ name = "eval";      dir = "apps\eval-dashboard"; port = 3002 }
)

# ---- prerequisites (report, never install)
$missing = @()
if (-not $Mock) {
    $ErrorActionPreference = "Continue"
    & python -c "import fastapi, uvicorn, pydantic, cryptography, jsonschema" 2>$null
    $ok = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = "Stop"
    if (-not $ok) { $missing += "Python packages (fastapi uvicorn pydantic cryptography jsonschema; scripts/allowed_deps.txt)" }
    if (-not (Test-PortFree $ApiPort)) { $missing += "port $ApiPort is already in use (pass -ApiPort N or stop that process)" }
}
if (-not $NoWeb) {
    if (-not (Test-Path (Join-Path $Root "node_modules"))) { $missing += "node_modules at the repo root (run 'npm ci' once, before demo day)" }
    foreach ($a in $apps) {
        if (-not (Test-Path (Join-Path $Root "$($a.dir)\package.json"))) { $missing += "$($a.dir) is missing" }
        if (-not (Test-PortFree $a.port)) { $missing += "port $($a.port) ($($a.name)) is already in use" }
    }
}
if ($missing.Count -gt 0) {
    Write-Host "Cannot start:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" }
    exit 1
}

# ---- backend
if (-not $Mock) {
    Write-Host "Starting backend on $api ..."
    $p = Start-Process -FilePath "python" -WorkingDirectory $Root -PassThru -WindowStyle Hidden `
        -ArgumentList @("-m", "uvicorn", "evolve_api.main:app", "--app-dir", "services/api", "--port", "$ApiPort") `
        -RedirectStandardOutput (Join-Path $LogDir "api.out.log") -RedirectStandardError (Join-Path $LogDir "api.err.log")
    $pids += $p.Id; Set-Content -Path $PidFile -Value $pids
    if (-not (Wait-Url "$api/api/demo/vignettes" 60)) {
        Write-Host "Backend did not become healthy in 60 s. Logs: $LogDir" -ForegroundColor Red
        Stop-Demo; exit 1
    }
    Write-Host "Backend healthy."
}

# ---- web apps (each app's own `dev` script pins its port)
if (-not $NoWeb) {
    if ($Mock) {
        Remove-Item Env:\NEXT_PUBLIC_API -ErrorAction SilentlyContinue
        Write-Host "OFFLINE MODE: citizen and counselor use their SIMULATED mock adapters. No backend calls."
    } else {
        $env:NEXT_PUBLIC_API = $api
    }
    $env:NEXT_TELEMETRY_DISABLED = "1"
    foreach ($a in $apps) {
        Write-Host "Starting $($a.name) on http://localhost:$($a.port) ..."
        $p = Start-Process -FilePath "npm.cmd" -WorkingDirectory (Join-Path $Root $a.dir) -PassThru -WindowStyle Hidden `
            -ArgumentList @("run", "dev") `
            -RedirectStandardOutput (Join-Path $LogDir "$($a.name).out.log") -RedirectStandardError (Join-Path $LogDir "$($a.name).err.log")
        $pids += $p.Id; Set-Content -Path $PidFile -Value $pids
    }
    foreach ($a in $apps) {
        if (Wait-Url "http://localhost:$($a.port)/en" 240) { Write-Host "$($a.name) up." }
        else { Write-Host "$($a.name) did not answer in 240 s. Log: $LogDir\$($a.name).*.log" -ForegroundColor Red }
    }
}

# ---- reset + stage + warm + print
if (-not $Mock) {
    & (Join-Path $PSScriptRoot "reset_demo.ps1") -Api $api -NoWarm:$NoWeb
} else {
    Write-Host ""
    Write-Host "Mock mode: partner IDs V1A/V1B ... V5A/V5B; counselor sign-in is SIMULATED; no reset needed."
    Write-Host "URLs: http://localhost:3000/en  http://localhost:3001/en  http://localhost:3002/en"
}
Write-Host ""
Write-Host "Running. PIDs in $PidFile, logs in $LogDir. Stop with: scripts\demo\run_local.ps1 -Stop"
exit 0
