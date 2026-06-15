# =====================================================================
#  start-bot.ps1
#  --------------------------------------------------------------------
#  Convenience launcher: runs the bot manually in this window, using the
#  virtual environment's Python. (Same thing the auto-start task runs.)
#
#  HOW TO RUN:   .\start-bot.ps1
#  Press Ctrl+C to stop.
# =====================================================================

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot
$Python     = Join-Path $ProjectDir ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: virtual environment not found. From this folder run:" -ForegroundColor Red
    Write-Host "       python -m venv .venv"
    Write-Host "       .venv\Scripts\Activate.ps1"
    Write-Host "       pip install -r requirements.txt"
    exit 1
}

Set-Location $ProjectDir

# Run the bot. Capture all output (including any startup crash that happens
# before the bot's own logging kicks in) to bot-console.log, while ALSO
# showing it on screen when run interactively. This file is our safety net
# for diagnosing problems when the bot is launched by Task Scheduler.
$consoleLog = Join-Path $ProjectDir "bot-console.log"
& $Python (Join-Path $ProjectDir "main.py") 2>&1 | Tee-Object -FilePath $consoleLog -Append
