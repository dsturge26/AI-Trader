# =====================================================================
#  install-autostart.ps1
#  --------------------------------------------------------------------
#  Sets up AI-Trader to start automatically every time you log in to
#  Windows, and to restart itself if it ever crashes. Run this ONCE.
#
#  HOW TO RUN:
#     1. Open PowerShell.
#     2. cd into this folder, e.g.:   cd $HOME\ai-trader
#     3. Run:                         .\install-autostart.ps1
#
#  It registers a Windows "Scheduled Task" named "AI-Trader". You do NOT
#  need administrator rights for this (it runs under your own account,
#  when you're logged in — perfect for an always-on home PC).
# =====================================================================

$ErrorActionPreference = "Stop"
$TaskName   = "AI-Trader"
$ProjectDir = $PSScriptRoot                                   # this script's folder
$Python     = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$MainPy     = Join-Path $ProjectDir "main.py"

Write-Host ""
Write-Host "=== AI-Trader auto-start installer ===" -ForegroundColor Cyan
Write-Host "Project folder: $ProjectDir"

# --- Safety checks: make sure the pieces exist before we schedule anything ---
if (-not (Test-Path $Python)) {
    Write-Host "ERROR: Could not find the virtual environment Python at:" -ForegroundColor Red
    Write-Host "       $Python"
    Write-Host "Did you finish Steps 2-3? From this folder run:" -ForegroundColor Yellow
    Write-Host "       python -m venv .venv"
    Write-Host "       .venv\Scripts\Activate.ps1"
    Write-Host "       pip install -r requirements.txt"
    exit 1
}
if (-not (Test-Path $MainPy)) {
    Write-Host "ERROR: main.py not found in $ProjectDir. Are you in the right folder?" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path (Join-Path $ProjectDir ".env"))) {
    Write-Host "WARNING: No .env file found yet. The bot needs your Alpaca keys." -ForegroundColor Yellow
    Write-Host "         Do Step 5 (copy .env.example to .env and add your keys) before it can trade."
    Write-Host ""
}

# --- Define the scheduled task ---------------------------------------
# Action: run the venv's python on main.py, starting in the project folder
# (so it finds .env, writes to logs\, and sees the KILL_SWITCH file).
$action = New-ScheduledTaskAction -Execute $Python `
                                  -Argument "`"$MainPy`"" `
                                  -WorkingDirectory $ProjectDir

# Trigger: every time you log on to Windows.
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME

# Settings: keep it running (no time limit), restart up to 3x if it crashes,
# and start it even if the PC was busy/asleep when you logged in.
$settings = New-ScheduledTaskSettingsSet `
                -AllowStartIfOnBatteries `
                -DontStopIfGoingOnBatteries `
                -StartWhenAvailable `
                -RestartCount 3 `
                -RestartInterval (New-TimeSpan -Minutes 1) `
                -ExecutionTimeLimit ([TimeSpan]::Zero)        # 0 = run forever

# Run under your own user account, only when you're logged in (no admin needed).
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive

# --- Register (or replace) the task ----------------------------------
Register-ScheduledTask -TaskName $TaskName `
                       -Action $action `
                       -Trigger $trigger `
                       -Settings $settings `
                       -Principal $principal `
                       -Description "Autonomous paper/live stock-trading bot (AI-Trader)." `
                       -Force | Out-Null

Write-Host ""
Write-Host "SUCCESS: Scheduled task '$TaskName' installed." -ForegroundColor Green
Write-Host "It will start automatically each time you log in to Windows."
Write-Host ""

# --- Start it right now so you don't have to log out/in --------------
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 2
$state = (Get-ScheduledTask -TaskName $TaskName).State
Write-Host "Started it now. Current state: $state" -ForegroundColor Green
Write-Host ""
Write-Host "WHAT TO DO NEXT:" -ForegroundColor Cyan
Write-Host "  * Watch what it's doing (live log):"
Write-Host "      Get-Content `"logs\trader-`$(Get-Date -Format yyyy-MM-dd).log`" -Wait"
Write-Host "  * Emergency stop trading (bot keeps running, just won't trade):"
Write-Host "      New-Item KILL_SWITCH        (delete it to resume: Remove-Item KILL_SWITCH)"
Write-Host "  * Stop / remove auto-start entirely:"
Write-Host "      .\uninstall-autostart.ps1"
Write-Host ""
Write-Host "NOTE: This runs while you are logged in. If you log out, it pauses;"
Write-Host "it resumes automatically next time you log in. For a true always-on"
Write-Host "home PC that stays logged in, that's exactly what you want."
