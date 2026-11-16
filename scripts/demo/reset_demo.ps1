# reset_demo.ps1 - reseed the evolve demo, pre-stage V3, warm the pages, print partner IDs, counselor login
# and URLs (R-DEMO-1). SIMULATED environment, synthetic data only. Windows PowerShell 5.1+ or PowerShell 7.
# ASCII-only on purpose (PowerShell 5.1 misreads UTF-8 files without a BOM).
#
#   powershell -ExecutionPolicy Bypass -File scripts\demo\reset_demo.ps1 [-Api URL] [-Web URL] [-Counselor URL]
#                                                                       [-Eval URL] [-NoWarm] [-NoStage]
param(
    [string]$Api = $(if ($env:EVOLVE_API) { $env:EVOLVE_API } else { "http://localhost:8000" }),
    [string]$Web = "http://localhost:3000",
    [string]$Counselor = "http://localhost:3001",
    [string]$Eval = "http://localhost:3002",
    [switch]$NoWarm,
    [switch]$NoStage
)
$ErrorActionPreference = "Stop"

function Post-Json([string]$path, $body, [string]$token) {
    $h = @{}
    if ($token) { $h["Authorization"] = "Bearer $token" }
    $json = if ($body) { $body | ConvertTo-Json -Compress } else { "{}" }
    return Invoke-RestMethod -Method Post -Uri ($Api + $path) -Headers $h -ContentType "application/json" -Body $json -TimeoutSec 30
}

Write-Host "== evolve demo reset (SIMULATED, synthetic data only)"
Write-Host "   api=$Api"
try {
    $reset = Post-Json "/api/demo/reset" $null $null
} catch {
    Write-Host "FAIL: backend not reachable at $Api ($($_.Exception.Message))" -ForegroundColor Red
    exit 1
}
Write-Host ("   reset -> " + ($reset | ConvertTo-Json -Compress))
if ($reset.status -ne "ok") { Write-Host "FAIL: reset did not return status ok" -ForegroundColor Red; exit 1 }

# Pre-stage V3: its locked records (explainer, gate-probe control) exist only after the couple check has run.
if (-not $NoStage) {
    try {
        $t = (Post-Json "/api/session" @{ partner_id = "V3A" } $null).token
        Post-Json "/api/consents" @{ counterpart = "V3B" } $t | Out-Null
        Post-Json "/api/demo/simulate-partner-consent" @{ couple_id = "V3" } $null | Out-Null
        $c = Post-Json "/api/couples/V3/compatibility" $null $t
        Write-Host ("   staged V3 (SIMULATED partner consent): compatible=" + $c.apsi.compatible + ", records for V3A ready")
    } catch {
        Write-Host "WARN: could not pre-stage V3 ($($_.Exception.Message)). Run the V3 check by hand." -ForegroundColor Yellow
    }
}

$vig = Invoke-RestMethod -Method Get -Uri "$Api/api/demo/vignettes" -TimeoutSec 10
# Demo beat per vignette (docs/demo/DEMO-SCRIPT.md). No genotype data is printed here.
$beat = @{
    "V1" = "LIVE  1:30  shared finding -> counselor handoff (trigger a). Sign in as A."
    "V2" = "SPARE       discordant complex locus -> confirmatory test for the carrier."
    "V3" = "LIVE  2:20  negative is not zero -> explainer. PRE-STAGED: sign in as A, open the explainer."
    "V4" = "LIVE  0:40  privacy test -> Compatible, nothing else revealed. Sign in as A, then B."
    "V5" = "SPARE       shared VUS in ROH -> held for counselor review, no Compatible headline."
}
Write-Host ""
Write-Host "== Partner IDs per vignette (SIMULATED sign-in: $Web/en/sign-in)"
$n = 0
foreach ($r in $vig) {
    $n++
    Write-Host ("  {0,-3} A={1,-5} B={2,-5} {3}" -f $r.couple_id, $r.partner_ids[0], $r.partner_ids[1], $r.label)
    Write-Host ("        " + $beat[$r.couple_id])
}
if ($n -ne 5) { Write-Host "WARN: expected 5 vignettes, got $n" -ForegroundColor Yellow }

Write-Host ""
Write-Host "== Counselor login (SIMULATED): $Counselor/en/sign-in -> 'Sign in (simulated)' -> switch 'On shift' ON"
Write-Host "   (shift defaults to OFF; case data is hidden until you go on shift - DECISIONS #40)"

function Invoke-Warm([string]$url) {
    try {
        $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 120
        Write-Host ("   {0}   {1}" -f [int]$resp.StatusCode, $url)
    } catch {
        if ($_.Exception.Response) { Write-Host ("   {0}   {1}" -f [int]$_.Exception.Response.StatusCode, $url) }
        else { Write-Host "   skip  $url (not reachable)" }
    }
}

if (-not $NoWarm) {
    Write-Host ""
    Write-Host "== Warming pages (first compile of each route in next dev is slow)"
    foreach ($p in @("/en", "/en/sign-in", "/en/home", "/en/results", "/en/results/explainer", "/en/compatibility", "/en/care-plan", "/ar/home")) {
        Invoke-Warm ($Web + $p)
    }
    foreach ($p in @("/en/sign-in", "/en/queue")) { Invoke-Warm ($Counselor + $p) }
    Invoke-Warm ($Eval + "/en")
}

Write-Host ""
Write-Host "== URLs"
Write-Host "   citizen    $Web/en"
Write-Host "   counselor  $Counselor/en"
Write-Host "   eval       $Eval/en   (gate-probe panel + guardrail feed)"
Write-Host "   api        $Api/api/demo/vignettes"
Write-Host "Follow docs/demo/DEMO-SCRIPT.md. Terminal fallback for the gate probe: python scripts\demo\gate_probe.py --api $Api"
exit 0
