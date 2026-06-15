# =====================================================================
#  uninstall-autostart.ps1
#  --------------------------------------------------------------------
#  Stops the AI-Trader bot and removes its auto-start task completely.
#
#  HOW TO RUN:   .\uninstall-autostart.ps1
# =====================================================================

$ErrorActionPreference = "SilentlyContinue"
$TaskName = "AI-Trader"

$task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -eq $task) {
    Write-Host "Nothing to do: there is no scheduled task named '$TaskName'." -ForegroundColor Yellow
    exit 0
}

Write-Host "Stopping the bot..." -ForegroundColor Cyan
Stop-ScheduledTask  -TaskName $TaskName -ErrorAction SilentlyContinue

Write-Host "Removing the auto-start task '$TaskName'..." -ForegroundColor Cyan
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false

Write-Host "Done. AI-Trader will no longer start automatically." -ForegroundColor Green
Write-Host "(Your code, .env, and logs are untouched. You can still run it"
Write-Host " manually any time with:  .\start-bot.ps1 )"
