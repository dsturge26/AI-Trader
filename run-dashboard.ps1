# =====================================================================
#  run-dashboard.ps1
#  --------------------------------------------------------------------
#  Launches the live web dashboard, then opens it in your browser. Shows
#  your account balance, open positions, and full buy/sell history, and
#  refreshes every 15 seconds (with a Refresh button too).
#
#  HOW TO RUN:   .\run-dashboard.ps1
#  Optional port: .\run-dashboard.ps1 9000
#  Press Ctrl+C in this window to stop the dashboard.
#
#  It is READ-ONLY: it never places or cancels an order.
# =====================================================================

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot
$Python     = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$Port       = if ($args.Count -ge 1) { $args[0] } else { "8080" }

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: virtual environment not found. From this folder run:" -ForegroundColor Red
    Write-Host "       python -m venv .venv"
    Write-Host "       .venv\Scripts\Activate.ps1"
    Write-Host "       pip install -r requirements.txt"
    exit 1
}

Set-Location $ProjectDir

# Open the browser a moment after the server starts.
Start-Job { Start-Sleep -Seconds 2; Start-Process "http://localhost:$using:Port" } | Out-Null

& $Python (Join-Path $ProjectDir "dashboard.py") $Port
