# =====================================================================
#  uninstall-startup.ps1
#  --------------------------------------------------------------------
#  Stops the bot and removes the auto-start-at-login shortcut.
#
#  HOW TO RUN:   .\uninstall-startup.ps1
# =====================================================================

$ProjectDir = $PSScriptRoot

# Stop the running bot, if any.
& (Join-Path $ProjectDir "stop-bot.ps1")

# Remove the Startup-folder shortcut.
$startupDir   = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupDir "AI-Trader.lnk"
if (Test-Path $shortcutPath) {
    Remove-Item $shortcutPath -Force
    Write-Host "Removed auto-start shortcut: $shortcutPath" -ForegroundColor Green
} else {
    Write-Host "No auto-start shortcut found (nothing to remove)." -ForegroundColor Yellow
}

Write-Host "Done. AI-Trader will no longer start at login."
Write-Host "(Your code, .env, and logs are untouched.)"
