# =====================================================================
#  check-ready.ps1
#  --------------------------------------------------------------------
#  Pre-flight check: is the bot set up to run and trade automatically?
#  Prints a simple PASS / FAIL checklist. Run it any time:
#
#      .\check-ready.ps1
# =====================================================================

$ProjectDir = $PSScriptRoot
$allGood = $true

Write-Host ""
Write-Host "=== AI-Trader readiness check ===" -ForegroundColor Cyan
Write-Host ""

# 1) .env present, with real keys
$envPath = Join-Path $ProjectDir ".env"
if (Test-Path $envPath) {
    $envText = Get-Content $envPath -Raw
    if ($envText -match 'ALPACA_API_KEY=\S+' -and $envText -notmatch 'your_key_here') {
        Write-Host "[PASS] .env file is present and has your API keys" -ForegroundColor Green
    } else {
        Write-Host "[FAIL] .env is missing your API keys (Step 5)" -ForegroundColor Red
        $allGood = $false
    }
    # Paper vs live
    if ($envText -match '(?im)^\s*ALPACA_PAPER\s*=\s*true') {
        Write-Host "[PASS] Paper trading mode (fake money) - safe" -ForegroundColor Green
    } else {
        Write-Host "[WARN] ALPACA_PAPER is not 'true' -> this would use REAL money" -ForegroundColor Yellow
    }
} else {
    Write-Host "[FAIL] No .env file found (Step 5)" -ForegroundColor Red
    $allGood = $false
}

# 2) Kill switch must be OFF (file absent) for trading to happen
if (Test-Path (Join-Path $ProjectDir "KILL_SWITCH")) {
    Write-Host "[FAIL] KILL_SWITCH file exists -> trading is HALTED" -ForegroundColor Red
    Write-Host "       Fix: Remove-Item KILL_SWITCH" -ForegroundColor Red
    $allGood = $false
} else {
    Write-Host "[PASS] No kill switch present -> trading is allowed" -ForegroundColor Green
}

# 3) The bot process is actually running
$proc = Get-CimInstance Win32_Process -Filter "Name='python.exe'" -ErrorAction SilentlyContinue |
        Where-Object { $_.CommandLine -like "*main.py*" } | Select-Object -First 1
if ($proc) {
    Write-Host "[PASS] The bot is running right now (PID $($proc.ProcessId))" -ForegroundColor Green
} else {
    Write-Host "[FAIL] The bot is NOT running" -ForegroundColor Red
    Write-Host "       Fix: .\run-bot-background.ps1" -ForegroundColor Red
    $allGood = $false
}

# 4) Auto-start at login is installed
$startupShortcut = Join-Path ([Environment]::GetFolderPath('Startup')) "AI-Trader.lnk"
if (Test-Path $startupShortcut) {
    Write-Host "[PASS] Auto-start at login is installed" -ForegroundColor Green
} else {
    Write-Host "[WARN] Auto-start at login is NOT installed" -ForegroundColor Yellow
    Write-Host "       Fix: .\install-startup.ps1" -ForegroundColor Yellow
}

Write-Host ""
if ($allGood) {
    Write-Host "READY: the bot is running and free to trade when the market opens." -ForegroundColor Green
    Write-Host "It will do its one daily check within ~15 minutes of the 9:30am ET open." -ForegroundColor Green
} else {
    Write-Host "NOT READY: fix the [FAIL] item(s) above, then run this check again." -ForegroundColor Red
}
Write-Host ""
