# AI-Trader — Everyday Commands Cheat Sheet

> ⚠️ These are **separate** commands — pick the ONE you need.
> Do **not** run them all in a row (they contradict each other).
>
> First, always move into the project folder:
> ```powershell
> cd $HOME\ai-trader
> ```

---

## 👀 See what the bot is doing (the two you'll use most)

Show the last 20 log lines (what it most recently decided and why):
```powershell
Get-Content "logs\trader-$(Get-Date -Format yyyy-MM-dd).log" -Tail 20
```

Watch the log live — new lines appear as they happen (press **Ctrl+C** to stop
watching; this does NOT stop the bot):
```powershell
Get-Content "logs\trader-$(Get-Date -Format yyyy-MM-dd).log" -Wait
```

---

## ✅ Check the bot is alive

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" | Select-Object ProcessId, CommandLine
```
Seeing **two** `python.exe` lines is normal on your PC — it's the Microsoft
Store Python launcher plus the real bot. It's still just **one** bot.

---

## 🛑 Stop trading immediately (the kill switch)

Halt all trading but leave the bot running (it just won't place orders):
```powershell
New-Item KILL_SWITCH
```
Resume trading later:
```powershell
Remove-Item KILL_SWITCH
```

---

## ⏯️ Start / stop the bot program

Stop the bot completely:
```powershell
.\stop-bot.ps1
```

Start it again in the background:
```powershell
.\run-bot-background.ps1
```

Run it in the current window so you can watch it live (Ctrl+C to stop):
```powershell
.\start-bot.ps1
```

---

## 🔁 Auto-start at login

It already auto-starts every time you log in to Windows. To turn that off:
```powershell
.\uninstall-startup.ps1
```
To turn it back on (and start it now):
```powershell
.\install-startup.ps1
```

---

## 📈 What "normal" looks like

- **Market closed** (nights/weekends/holidays): the log repeats
  `Market is closed right now. Doing nothing (this is normal).` ✅
- **Market open**, most days: it logs a plain-English **HOLD** with the reason.
  Doing nothing most days is the strategy being patient — not a bug. ✅
- It only acts **about once a day**, on completed daily price bars.

US markets are open roughly **9:30am–4:00pm Eastern, Monday–Friday**.

---

## 💵 Reminder: this is PAPER money

The bot is in paper-trading mode (fake money) by default. It will refuse to
use real money unless you deliberately change `ALPACA_PAPER=false` in `.env`
**and** type a confirmation phrase when it starts. See section 10 of `README.md`
before ever considering that — and watch paper mode for a good while first.
