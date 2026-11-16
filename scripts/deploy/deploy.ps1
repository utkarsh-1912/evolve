# deploy.ps1 - one entry point for both deployment targets (DECISIONS #62). SIMULATED environment, synthetic data.
#   powershell -ExecutionPolicy Bypass -File scripts\deploy\deploy.ps1 -Target vm [-EnvFile deploy\vm\.env] [-DryRun]
#   powershell -ExecutionPolicy Bypass -File scripts\deploy\deploy.ps1 -Target vercel-render [-EnvFile deploy\vercel-render\.env]
# vm:            validates the env file, runs `docker compose config`, then (unless -DryRun) builds and starts the stack.
# vercel-render: validates the env file and prints the dashboard steps. It never runs a cloud CLI or creates accounts.
# Secrets are never printed. ASCII-only on purpose (PowerShell 5.1 + no BOM).
param(
    [Parameter(Mandatory = $true)][ValidateSet("vm", "vercel-render")][string]$Target,
    [string]$EnvFile,
    [switch]$DryRun
)
$ErrorActionPreference = "Stop"
$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
if (-not $EnvFile) { $EnvFile = Join-Path $Root "deploy\$Target\.env" }
if (-not (Test-Path $EnvFile)) {
    Write-Host "FAIL: env file not found: $EnvFile" -ForegroundColor Red
    Write-Host "      Copy deploy\$Target\env.example to deploy\$Target\.env and fill it in."
    exit 1
}
$EnvFile = (Resolve-Path $EnvFile).Path

# ---- parse KEY=VALUE (comments and blank lines ignored)
$cfg = @{}
foreach ($line in Get-Content $EnvFile) {
    $t = $line.Trim()
    if (-not $t -or $t.StartsWith("#")) { continue }
    $i = $t.IndexOf("=")
    if ($i -lt 1) { continue }
    $cfg[$t.Substring(0, $i).Trim()] = $t.Substring($i + 1).Trim()
}

$errors = New-Object System.Collections.ArrayList
$warns = New-Object System.Collections.ArrayList
function Need([string]$k) { if (-not $cfg[$k]) { [void]$errors.Add("missing $k") } }

$required = @("DEPLOY_TARGET", "API_URL", "CITIZEN_URL", "COUNSELOR_URL", "EVAL_URL", "CORS_ORIGINS")
if ($Target -eq "vm") { $required += @("APP_DOMAIN", "ACME_EMAIL") }
$required | ForEach-Object { Need $_ }

if ($cfg["DEPLOY_TARGET"] -and $cfg["DEPLOY_TARGET"] -ne $Target) {
    [void]$errors.Add("DEPLOY_TARGET=$($cfg['DEPLOY_TARGET']) does not match -Target $Target")
}
foreach ($k in @("API_URL", "CITIZEN_URL", "COUNSELOR_URL", "EVAL_URL")) {
    $v = $cfg[$k]
    if ($v -and -not $v.StartsWith("https://")) { [void]$errors.Add("$k must start with https://") }
    if ($v -and $v.EndsWith("/")) { [void]$errors.Add("$k must not end with /") }
}
if ($cfg["CORS_ORIGINS"]) {
    $cors = @($cfg["CORS_ORIGINS"].Split(",") | ForEach-Object { $_.Trim() } | Where-Object { $_ } | Sort-Object)
    $apps = @($cfg["CITIZEN_URL"], $cfg["COUNSELOR_URL"], $cfg["EVAL_URL"] | Sort-Object)
    if (($cors -join ",") -ne ($apps -join ",")) {
        [void]$errors.Add("CORS_ORIGINS must list exactly CITIZEN_URL, COUNSELOR_URL and EVAL_URL")
    }
}
if ($Target -eq "vm" -and $cfg["APP_DOMAIN"]) {
    $d = $cfg["APP_DOMAIN"]
    $expect = @{ CITIZEN_URL = "https://app.$d"; COUNSELOR_URL = "https://counselor.$d"; EVAL_URL = "https://eval.$d"; API_URL = "https://api.$d" }
    foreach ($k in $expect.Keys) {
        if ($cfg[$k] -and $cfg[$k] -ne $expect[$k]) { [void]$errors.Add("$k should be $($expect[$k]) (Caddyfile subdomains)") }
    }
}
$joined = ($cfg.Values -join " ")
if ($joined -match "example\.(org|com)") {
    if ($DryRun) { [void]$warns.Add("placeholder example.* values (fine for a dry run, not for a real deploy)") }
    else { [void]$errors.Add("placeholder example.* values: fill in your real domain/URLs") }
}
if ($cfg["SARVAM_API_KEY"]) { Write-Host "SARVAM_API_KEY: set (not printed) -> AI draft uses Sarvam (counselor-side only)" }
else { [void]$warns.Add("SARVAM_API_KEY empty -> counselor AI draft runs on the offline stub") }

Write-Host "== evolve deploy: target=$Target  env=$EnvFile  dryRun=$DryRun"
$warns | ForEach-Object { Write-Host "WARN: $_" -ForegroundColor Yellow }
if ($errors.Count -gt 0) {
    $errors | ForEach-Object { Write-Host "FAIL: $_" -ForegroundColor Red }
    exit 1
}
Write-Host "env file OK"

if ($Target -eq "vm") {
    $compose = Join-Path $Root "deploy\vm\docker-compose.yml"
    if (-not (Get-Command docker -ErrorAction SilentlyContinue)) { Write-Host "FAIL: docker not found" -ForegroundColor Red; exit 1 }
    Write-Host "> docker compose --env-file <env> -f deploy/vm/docker-compose.yml config --quiet"
    $ErrorActionPreference = "Continue"
    & docker compose --env-file $EnvFile -f $compose config --quiet
    $rc = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ($rc -ne 0) { Write-Host "FAIL: compose config invalid" -ForegroundColor Red; exit 1 }
    Write-Host "compose config OK"
    Write-Host ""
    Write-Host "Before starting: DNS A/AAAA for app., counselor., eval., api.$($cfg['APP_DOMAIN']) -> this VM; ports 80/443 open;"
    Write-Host "eval data synced (npm run sync -w evolve-eval-dashboard) and committed."
    if ($DryRun) {
        Write-Host "DRY RUN: would now run:"
        Write-Host "  docker compose --env-file `"$EnvFile`" -f deploy/vm/docker-compose.yml up -d --build"
        exit 0
    }
    $ErrorActionPreference = "Continue"
    & docker info *> $null
    $up = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = "Stop"
    if (-not $up) { Write-Host "FAIL: Docker daemon is not running" -ForegroundColor Red; exit 1 }
    & docker compose --env-file $EnvFile -f $compose up -d --build
    if ($LASTEXITCODE -ne 0) { Write-Host "FAIL: compose up" -ForegroundColor Red; exit 1 }
    Write-Host ""
    Write-Host "Started. The 'reset' job reseeds and stages V3: docker compose -f deploy/vm/docker-compose.yml logs reset"
    Write-Host "URLs: $($cfg['CITIZEN_URL'])/en  $($cfg['COUNSELOR_URL'])/en  $($cfg['EVAL_URL'])/en  $($cfg['API_URL'])/api/demo/vignettes"
    Write-Host "Then run the smoke checklist in docs/demo/DEPLOY.md."
    exit 0
}

# ---- vercel-render: print the steps (no cloud CLI is run)
Write-Host ""
Write-Host "== Render (backend)"
Write-Host "  1. dashboard.render.com -> New -> Blueprint -> this repo; Blueprint path: deploy/vercel-render/render.yaml"
Write-Host "     (or New -> Web Service with the build/start commands from that file)."
Write-Host "  2. Environment: CORS_ORIGINS = $($cfg['CORS_ORIGINS'])"
Write-Host "                  SARVAM_API_KEY = <paste in the dashboard; leave unset for the offline stub>"
Write-Host "  3. Deploy; check $($cfg['API_URL'])/api/demo/vignettes returns 5 vignettes."
Write-Host ""
Write-Host "== Vercel (3 projects, settings in deploy/vercel-render/vercel-projects.md)"
foreach ($a in @(@("citizen", "apps/citizen", "evolve-citizen", "CITIZEN_URL"),
                 @("counselor", "apps/counselor", "evolve-counselor", "COUNSELOR_URL"),
                 @("eval", "apps/eval-dashboard", "evolve-eval-dashboard", "EVAL_URL"))) {
    Write-Host ("  {0}: Root Directory {1}; Install 'cd ../.. && npm ci'; Build 'cd ../.. && npm run build --ignore-scripts -w {2}'" -f $a[0], $a[1], $a[2])
    Write-Host ("       NEXT_PUBLIC_API = {0}; expected URL {1}" -f $cfg["API_URL"], $cfg[$a[3]])
}
Write-Host ""
Write-Host "== After all four are live"
Write-Host "  - If a Vercel URL differs from the env file, update CORS_ORIGINS on Render and redeploy the backend."
Write-Host "  - Render free instances sleep and lose in-memory state. Before each demo run:"
Write-Host "      python deploy/vm/reset_on_start.py $($cfg['API_URL'])"
Write-Host "  - Then run the smoke checklist in docs/demo/DEPLOY.md."
exit 0
