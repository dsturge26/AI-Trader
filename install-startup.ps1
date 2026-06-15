# =====================================================================
#  install-startup.ps1   (the RELIABLE auto-start method)
#  --------------------------------------------------------------------
#  Makes AI-Trader start automatically every time you log in to Windows,
#  using the Startup folder (which runs programs directly in your normal
#  session). No Task Scheduler, no admin rights, no special permissions.
#
#  Run this ONCE:   .\install-startup.ps1
# =====================================================================

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot
$bgScript   = Join-Path $ProjectDir "run-bot-background.ps1"

Write-Host ""
Write-Host "=== AI-Trader auto-start (Startup-folder method) ===" -ForegroundColor Cyan
Write-Host "Project folder: $ProjectDir"

# --- Clean up the old Task Scheduler task if it exists ----------------
# (It was failing to launch on this PC; we don't want it erroring at every
#  login. The Startup-folder method replaces it.)
$old = Get-ScheduledTask -TaskName "AI-Trader" -ErrorAction SilentlyContinue
if ($old) {
    Write-Host "Removing the old (non-working) scheduled task..." -ForegroundColor Yellow
    Stop-ScheduledTask  -TaskName "AI-Trader" -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName "AI-Trader" -Confirm:$false -ErrorAction SilentlyContinue
}

# --- Create a shortcut in the Startup folder --------------------------
# At login Windows runs everything in this folder. The shortcut launches
# PowerShell (hidden) which runs run-bot-background.ps1, which starts the
# bot hidden and exits.
$startupDir   = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupDir "AI-Trader.lnk"
$psExe        = (Get-Command powershell.exe).Source

$shell = New-Object -ComObject WScript.Shell
$sc = $shell.CreateShortcut($shortcutPath)
$sc.TargetPath       = $psExe
$sc.Arguments        = "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$bgScript`""
$sc.WorkingDirectory = $ProjectDir
$sc.WindowStyle      = 7            # 7 = minimized/hidden
$sc.Description       = "Start the AI-Trader bot at login"
$sc.Save()

Write-Host "Created auto-start shortcut:" -ForegroundColor Green
Write-Host "  $shortcutPath"
Write-Host ""

# --- Start it right now too -------------------------------------------
Write-Host "Starting the bot now..." -ForegroundColor Cyan
& $bgScript

Start-Sleep -Seconds 3
$running = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
           Where-Object { $_.CommandLine -like "*main.py*" }

Write-Host ""
if ($running) {
    Write-Host "CONFIRMED: the bot is running in the background (PID $($running.ProcessId))." -ForegroundColor Green
    Write-Host "It will also start automatically every time you log in to Windows."
} else {
    Write-Host "Hmm - it doesn't appear to be running. Check bot-error.log:" -ForegroundColor Yellow
    $errLog = Join-Path $ProjectDir "bot-error.log"
    if (Test-Path $errLog) { Get-Content $errLog -Tail 20 }
}

Write-Host ""
Write-Host "WHAT TO DO NEXT:" -ForegroundColor Cyan
Write-Host "  * Watch what it's doing (live log):"
Write-Host "      Get-Content `"logs\trader-`$(Get-Date -Format yyyy-MM-dd).log`" -Wait"
Write-Host "  * Stop the bot now:                 .\stop-bot.ps1"
Write-Host "  * Emergency halt trading only:      New-Item KILL_SWITCH   (resume: Remove-Item KILL_SWITCH)"
Write-Host "  * Remove auto-start at login:       .\uninstall-startup.ps1"
