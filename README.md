# AI-Trader 🤖📈

A **calm, beginner-friendly, autonomous stock-trading bot** in Python. It runs
on your always-on PC, looks at one stock about **once a day**, and decides to
**buy, sell, or do nothing** using one simple, well-known strategy — wrapped in
strict safety guardrails.

> **You said you're new to trading. This README assumes zero knowledge.**
> Every term is defined the first time it appears. No jargon without an
> explanation. Read the "Trading concepts" section before you run anything.

---

## ⚠️ The single most important thing

**This bot defaults to PAPER TRADING — fake money.** You can run it for weeks,
watch what it does, and lose nothing real. It will **refuse** to touch real
money unless you deliberately change a setting *and* type a confirmation phrase
when it starts. It will **never** switch to real money on its own.

Please run it in paper mode first. Real money is the *last* section of this
document, on purpose.

---

## Table of contents

1. [What this bot actually does](#1-what-this-bot-actually-does)
2. [Trading concepts in plain English](#2-trading-concepts-in-plain-english)
3. [The strategy: exactly when it buys and sells](#3-the-strategy-exactly-when-it-buys-and-sells)
4. [The safety guardrails](#4-the-safety-guardrails)
5. [The six modules (the architecture)](#5-the-six-modules-the-architecture)
6. [Setup — copy-paste steps](#6-setup--copy-paste-steps)
7. [Running it in paper mode](#7-running-it-in-paper-mode)
8. [Reading the logs](#8-reading-the-logs)
9. [The kill switch](#9-the-kill-switch)
10. [ONLY when you're ready: real money](#10-only-when-youre-ready-real-money)
11. [Honest limitations](#11-honest-limitations)

---

## 1. What this bot actually does

A "trading bot" sounds fancy, but ours is simple. On a timer, it repeats this
loop:

1. **Ask the broker for recent prices.** ("Broker" = the company that holds your
   money and places your orders. We use **Alpaca**, which has a free, friendly
   programming interface.)
2. **Do a little math** on those prices to produce two simple numbers
   (our "indicators" — defined below).
3. **Apply one rule** to those numbers to decide: buy, sell, or hold.
4. **Check the safety guardrails.** If the trade would break a money rule, it's
   blocked — no matter what the strategy wanted.
5. **Place the order** (only if allowed), through Alpaca.
6. **Write down what it did, and WHY,** in a plain-English log file.

It uses **daily bars** (one price summary per day), so it acts *at most about
once a day*. No frantic second-by-second trading. Calm and simple.

> **"Bar"** = one time period's price summary. A *daily* bar is one day's
> Open, High, Low, and Close prices. We mostly use the **Close** — the final
> price of the trading day.

---

## 2. Trading concepts in plain English

You only need to understand **two** indicators. An **"indicator"** is just a
number calculated from past prices that summarizes something useful. It does
**not** predict the future — it describes the past.

### 2a. Moving Average (the "trend line")

A **Simple Moving Average (SMA)** is the average closing price over the last N
days. We use **50 days**.

> **Everyday analogy:** Imagine weighing yourself every morning. Any single
> day is noisy (maybe you drank a lot of water last night). But the *average*
> of your last 50 mornings reveals the real **trend** — slowly up, or slowly
> down? An SMA does that for a stock price: it smooths out the daily noise so
> you can see the overall direction.

**How we use it:** it's our **trend filter**.
- If today's price is **above** its 50-day average → the stock is generally
  trending **up** (we call this "healthy").
- If it's **below** → trending **down** ("weak").

We only buy stocks that are trending up. "Don't fight the trend."

### 2b. RSI — the "cheap or expensive right now?" meter

**RSI** stands for **Relative Strength Index**. It's a number from **0 to 100**
that measures how much of a stock's recent movement (we use the last **14
days**) was *up* versus *down*.

- **RSI near 70 or above** → the price rose a lot, fast. We call this
  **"overbought"** — it might be getting expensive / due for a breather.
- **RSI near 30 or below** → the price fell a lot, fast. We call this
  **"oversold"** — it might be temporarily too cheap / beaten down.
- **RSI around 50** → nothing extreme is happening.

> **Everyday analogy:** Think of RSI as a **"how stretched is the rubber
> band?"** meter. Pull a rubber band far in one direction (a big, fast price
> move) and it tends to snap back. High RSI = stretched up (overbought).
> Low RSI = stretched down (oversold).

**How we use it:** it's our **timing** tool — *when* within a trend to act.

> **Reality check:** Neither indicator predicts the future, and both are
> sometimes wrong. A stock can stay "oversold" and keep falling. That's
> *exactly* why the guardrails in section 4 exist — to limit the damage when
> the strategy is wrong, which it sometimes will be.

---

## 3. The strategy: exactly when it buys and sells

We use one classic, conservative beginner strategy, sometimes called
**"buy the dip in an uptrend."** The whole idea in one sentence:

> **Only buy a *healthy* stock (uptrend) that has *temporarily* gotten cheap
> (low RSI); sell it once it gets expensive (high RSI) or stops being healthy
> (trend breaks).**

Here are the **exact rules** the code follows. Let:
- `price` = the latest daily closing price
- `sma` = the 50-day moving average (our trend line)
- `rsi` = the 14-day RSI (our 0–100 meter)

**It BUYS** (only if it currently owns *none* of the stock) when **both** are true:
- `price > sma` → the trend is **up** (healthy), **and**
- `rsi < 35` → it just **dipped** / looks cheap.

→ *"A healthy stock went on temporary sale. Buy some."*

**It SELLS** (only if it currently *owns* the stock) when **either** is true:
- `rsi > 70` → it got **expensive**; take the gains, **or**
- `price < sma` → the **uptrend broke**; get out to protect ourselves.

→ *"Either it got pricey, or it's no longer healthy. Exit."*

**It HOLDS (does nothing)** in every other case. **This will be most days, and
that is correct.** A good simple bot is patient and mostly idle.

The numbers (`50`, `14`, `35`, `70`) are standard, sensible defaults. They live
in your `.env` file so you can adjust them later — but you don't need to.

---

## 4. The safety guardrails

These are **non-negotiable** and live in your `.env`. The **risk module** checks
them on every cycle and can **VETO any trade**, even one the strategy loves.
Safety always wins.

| Guardrail | Default | Plain English |
|---|---|---|
| **`ACCOUNT_FLOOR`** | `$35` | If your total account value falls below this, **halt ALL trading.** Stops a small account from being ground to zero. |
| **`MAX_POSITION_NOTIONAL`** | `$25` | **Never** put more than this many dollars into the position. Caps the size of any single bet. ("Notional" = dollar value of the position.) |
| **`MAX_DAILY_LOSS`** | `$10` | If today's account value is down this much from where it **opened today**, **stop trading for the rest of the day.** A bad day can't snowball. |
| **Kill switch** | — | A file you can create to **stop everything instantly** (see section 9). |

> **"Equity"** = the total value of your account = your cash **plus** the
> current value of any stocks you hold.

---

## 5. The six modules (the architecture)

The bot is split into six small files, each with one job. This makes it easy to
read, trust, and change one piece without breaking the others.

| Module | File | What it does, in plain English |
|---|---|---|
| **1. Data feed** | `trader/data_feed.py` | The bot's **eyes**. Asks Alpaca for the last few months of daily prices and hands them back as a table. Touches no money. |
| **2. Indicators** | `trader/indicators.py` | The bot's **math**. Turns raw prices into the two numbers (50-day average and RSI). Computed by hand so nothing is a black box. |
| **3. Strategy** | `trader/strategy.py` | The bot's **brain**. Applies the one rule above and returns **buy / sell / hold** *plus a plain-English reason*. Touches no money. |
| **4. Execution** | `trader/execution.py` | The bot's **hands**. The **only** file that connects to your account, reads your balance, and places real orders. |
| **5. Risk** | `trader/risk.py` | The bot's **brakes**. The guardrails. Can **veto any trade** or halt everything. |
| **6. Main loop + logging** | `main.py`, `trader/logger.py` | The **conductor + scribe**. Runs the whole flow on a timer and writes every decision (and *why*) to a log file. |

`config.py` is a small 7th helper that loads your settings and contains the
real-money safety gate.

---

## 6. Setup — copy-paste steps

You need **Python 3.10 or newer**. Check with `python3 --version`.

### Step 1 — Get free Alpaca paper-trading keys

1. Sign up at **https://app.alpaca.markets/** (free).
2. In the dashboard, switch to **Paper Trading** (a toggle, usually top-left).
3. Find **API Keys** → **Generate** a new key.
4. Copy the **API Key ID** and the **Secret Key** somewhere safe. The secret is
   shown **once** — if you lose it, just regenerate.

> Paper and live accounts have **different** keys. Make sure you grabbed the
> **paper** ones.

### Step 2 — Get the code and install dependencies

```bash
# (You already have this folder. From inside it:)

# Create an isolated Python environment so we don't touch your system Python:
python3 -m venv .venv

# Activate it:
#   macOS / Linux:
source .venv/bin/activate
#   Windows (PowerShell):
#   .venv\Scripts\Activate.ps1

# Install the three dependencies:
pip install -r requirements.txt
```

### Step 3 — Create your .env file (where your keys live)

```bash
# Copy the template:
cp .env.example .env

# Now open .env in any text editor and paste your two paper keys in:
#   ALPACA_API_KEY=...your paper key id...
#   ALPACA_SECRET_KEY=...your paper secret...
#
# Leave ALPACA_PAPER=true   <-- this keeps you on FAKE money. Do not change it yet.
```

Your `.env` is **git-ignored**, so your secret keys are never committed or
shared.

---

## 7. Running it in paper mode

With your environment activated and `.env` filled in:

```bash
python main.py
```

You should see it start up and print something like:

```
Starting AI-Trader. Mode: PAPER (fake money). Symbol: SPY.
Guardrails: floor=$35.00  max-position=$25.00  max-daily-loss=$10.00
Entering main loop. Press Ctrl+C to stop.
Account: equity=$100000.00  open=$100000.00  position=$0.00
Indicators for SPY: price=$... 50-day-avg=$... RSI=...
Strategy decision: HOLD: ...plain-English reason...
No order placed this cycle.
```

What to expect:
- A fresh Alpaca paper account starts with **$100,000 of fake money**. Our
  guardrails (e.g. $25 max position) are tiny on purpose — they're designed to
  protect a *small real* account later, so on paper you'll see only small
  positions.
- **Most cycles it will HOLD.** That's normal and healthy. It only trades when
  its specific conditions line up — sometimes not for days.
- It wakes up about **once an hour** (to check the kill switch and the market
  clock) but takes a real decision **at most about once a day**.
- Leave it running. Press **Ctrl+C** anytime to stop it cleanly.

> **Tip:** To keep it running on your always-on PC after you close the terminal,
> you can use `nohup python main.py &` (macOS/Linux), Windows Task Scheduler, or
> a tool like `tmux`. Start by just running it in a terminal and watching it,
> though.
>
> **Windows users:** there are ready-made helper scripts in this folder:
> - `.\install-autostart.ps1` — sets up the bot to launch automatically every
>   time you log in (and restart itself if it crashes). Run once.
> - `.\uninstall-autostart.ps1` — removes that auto-start.
> - `.\start-bot.ps1` — run the bot manually in the current window.

---

## 8. Reading the logs

Every decision is written to **both your screen and a file**:

```
logs/trader-YYYY-MM-DD.log     (a new file each day)
```

Open today's file in any text editor, or tail it live:

```bash
# macOS / Linux — watch new lines appear in real time:
tail -f logs/trader-$(date +%F).log
```

Each line is a full English sentence, e.g.:

```
2026-06-15 14:30:01  INFO  Indicators for SPY: price=$542.10  50-day-avg=$535.40  RSI=28.6
2026-06-15 14:30:01  INFO  Strategy decision: BUY: The stock is in an UPTREND ... RSI is 28.6, below the 'cheap' line of 35. A healthy stock just dipped — that's our entry.
2026-06-15 14:30:02  INFO  Risk OK. BUY allowed: investing $25.00 (within the $25.00 per-position cap).
2026-06-15 14:30:02  INFO  ORDER PLACED: BUY $25.00 of SPY. (Alpaca order id: ...)
```

So you can always read back **what it did and exactly why.**

---

## 9. The kill switch

Your instant "STOP EVERYTHING" button. The bot checks for a file named
`KILL_SWITCH` every cycle. If it exists, the bot trades nothing.

```bash
# STOP all trading immediately (bot keeps running but won't trade):
touch KILL_SWITCH         # macOS / Linux
# Windows (PowerShell):  New-Item KILL_SWITCH

# RESUME trading later:
rm KILL_SWITCH            # macOS / Linux
# Windows (PowerShell):  Remove-Item KILL_SWITCH
```

To stop the **program** entirely, press **Ctrl+C** in its terminal.

---

## 10. ONLY when you're ready: real money

**Do not do this until you've watched paper mode for a good while and fully
understand what the bot does.** Trading real money can lose real money.

When you genuinely decide to go live:

1. In Alpaca, switch to your **Live** account and generate **live** API keys.
2. Put the **live** keys in `.env`.
3. Set `ALPACA_PAPER=false`.
4. **Fund the live account** with only money you can afford to lose — the
   guardrails assume a small account (e.g. a floor of $35, $25 max position).
5. Run `python main.py`. The bot will print a **loud warning** and make you
   type the exact phrase **`USE REAL MONEY`** before it does anything. If you
   don't type it exactly, it aborts. It will **never** flip to live on its own.

```
##################################################################
#   !!!  LIVE TRADING IS ENABLED  —  THIS USES REAL MONEY  !!!    #
#   ... press Ctrl+C NOW if you didn't mean this ...             #
##################################################################
Type exactly  USE REAL MONEY  to proceed (anything else aborts):
```

> If the bot runs without an interactive terminal (e.g. as a background
> service) and live mode is on, it **refuses to trade** rather than guess —
> it fails safe.

---

## 11. Honest limitations

I'm telling you these plainly so you trust the tool:

- **No strategy wins all the time.** This one will have losing trades. The
  guardrails limit damage; they don't prevent every loss.
- **One stock, one simple rule.** This is a learning tool, not a
  professional-grade system. It is intentionally minimal.
- **Free market data is slightly delayed** (~15 min) and we trade on
  *completed daily bars*, so the bot is never reacting to live ticks. That's
  by design — calm, not fast.
- **It only goes "long"** (buys, then sells what it bought). It never
  "short-sells" (betting a price will fall), which is riskier and not
  beginner-appropriate.
- **Past performance never guarantees future results.** Start on paper, keep
  position sizes tiny, and only ever risk money you can afford to lose.

Happy (paper) trading. Read the logs, learn what the bot sees, and you'll pick
up real intuition for trends and timing along the way.
```

