# =====================================================================
#  run-bot-background.ps1
#  --------------------------------------------------------------------
#  Starts the bot HIDDEN in the background (no visible window) and then
#  exits, leaving the bot running. Safe to run twice: if the bot is
#  already running, it won't start a second copy.
#
#  This is what both "start it now" and the auto-start-at-login shortcut
#  call. It runs in your normal logged-in session — exactly like running
#  start-bot.ps1 by hand — so it just works.
# =====================================================================

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot
$Python     = Join-Path $ProjectDir ".venv\Scripts\python.exe"
$MainPy     = Join-Path $ProjectDir "main.py"

if (-not (Test-Path $Python)) {
    Write-Host "ERROR: virtual environment not found at $Python" -ForegroundColor Red
    Write-Host "Finish setup first: python -m venv .venv ; pip install -r requirements.txt"
    exit 1
}

# Don't launch a second copy if one is already running.
$existing = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
            Where-Object { $_.CommandLine -like "*main.py*" }
if ($existing) {
    Write-Host "Bot is already running (PID $($existing.ProcessId)). Nothing to do." -ForegroundColor Yellow
    return
}

# Launch hidden. Capture stdout/stderr to files so any startup problem is
# visible (the bot also writes its own plain-English log under logs\).
$outLog = Join-Path $ProjectDir "bot-console.log"
$errLog = Join-Path $ProjectDir "bot-error.log"

$proc = Start-Process -FilePath $Python `
                      -ArgumentList "`"$MainPy`"" `
                      -WorkingDirectory $ProjectDir `
                      -WindowStyle Hidden `
                      -RedirectStandardOutput $outLog `
                      -RedirectStandardError  $errLog `
                      -PassThru

Start-Sleep -Seconds 2
if ($proc -and -not $proc.HasExited) {
    Write-Host "Bot started in the background (PID $($proc.Id))." -ForegroundColor Green
} else {
    Write-Host "Bot exited immediately. Check bot-error.log for the reason:" -ForegroundColor Red
    if (Test-Path $errLog) { Get-Content $errLog -Tail 20 }
}
