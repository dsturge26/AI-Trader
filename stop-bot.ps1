# =====================================================================
#  stop-bot.ps1
#  --------------------------------------------------------------------
#  Stops the running bot (the background python process). This does NOT
#  remove auto-start — it will come back next time you log in. To remove
#  auto-start entirely, run .\uninstall-startup.ps1
#
#  HOW TO RUN:   .\stop-bot.ps1
# =====================================================================

$procs = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
         Where-Object { $_.CommandLine -like "*main.py*" }

if (-not $procs) {
    Write-Host "The bot is not running. Nothing to stop." -ForegroundColor Yellow
    return
}

foreach ($p in $procs) {
    Write-Host "Stopping bot (PID $($p.ProcessId))..." -ForegroundColor Cyan
    Stop-Process -Id $p.ProcessId -Force
}
Write-Host "Bot stopped." -ForegroundColor Green
