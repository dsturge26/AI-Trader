"""
main.py  —  The conductor. Runs everything on a calm, once-a-day rhythm.

Plain English, the whole flow in order:
    1. Load settings from .env  (config).
    2. If you asked for REAL money, make you confirm it loudly (safety gate).
    3. Wake up on a timer (default: once an hour).
    4. Each time it wakes up:
         a. Check the global guardrails (kill switch, account floor, daily
            loss). If any fire, do nothing and log why.
         b. Only act when the market is open AND we haven't already acted
            today (so it trades AT MOST about once a day, calmly).
         c. Get recent daily prices  (data_feed).
         d. Compute the indicators    (indicators).
         e. Ask the strategy what to do (strategy).
         f. Run the risk checks on that decision (risk).
         g. If allowed, place the order (execution).
         h. Write a plain-English sentence about what happened (logger).

To stop the bot: press Ctrl+C, or create the KILL_SWITCH file.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone

from config import confirm_live_trading_or_exit, load_config
from trader import indicators, risk, strategy
from trader.data_feed import DataFeed
from trader.execution import Execution
from trader.logger import setup_logger
from trader.strategy import Action


def acquire_single_instance_lock(lock_path: str):
    """
    Make sure only ONE copy of the bot can run at a time.

    Plain English:
        If you accidentally start the bot twice, two copies would both try to
        trade the same account and could double up on orders. To prevent that,
        we grab an exclusive lock on a small file. The operating system holds
        this lock for as long as this program is alive and releases it AUTOMATIC-
        ALLY if the program ever stops or crashes — so there's no stale lock to
        clean up by hand.

    Returns the open file handle (keep it alive for the whole run) if we got the
    lock, or None if another copy already holds it.
    """
    f = open(lock_path, "w")
    try:
        if os.name == "nt":               # Windows
            import msvcrt
            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:                              # macOS / Linux
            import fcntl
            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        f.close()
        return None
    return f


def run_once(cfg, feed: DataFeed, execu: Execution, log) -> bool:
    """
    One full think-and-maybe-trade cycle. Safe to call repeatedly.

    Returns True if the market was open this cycle (i.e. it was a real
    "trading day" attempt), so the caller can avoid acting again until
    tomorrow. Returns False if nothing tradable happened (market closed,
    or a global halt fired).
    """

    # --- (a) Global guardrails first: these can halt everything ---------
    snap = execu.snapshot(cfg.symbol)
    halt = risk.check_global_halts(
        snap,
        account_floor=cfg.account_floor,
        max_daily_loss=cfg.max_daily_loss,
        kill_switch_path=cfg.kill_switch_path,
    )
    log.info("Account: equity=$%.2f  open=$%.2f  position=$%.2f",
             snap.equity, snap.last_equity, snap.position_notional)
    if not halt.allowed:
        log.warning(halt.reason)
        return False

    # --- (b) Only trade when the market is actually open ---------------
    if not execu.market_is_open():
        log.info("Market is closed right now. Doing nothing (this is normal).")
        return False

    # --- (c) Get prices, (d) indicators -------------------------------
    df = feed.get_daily_bars(cfg.symbol, lookback_days=max(220, cfg.sma_trend_period * 3))
    df = indicators.compute_indicators(df, cfg.sma_trend_period, cfg.rsi_period)

    # --- (e) Ask the strategy -----------------------------------------
    holding = execu.holding(cfg.symbol)
    decision = strategy.decide(
        df,
        holding=holding,
        rsi_buy_below=cfg.rsi_buy_below,
        rsi_sell_above=cfg.rsi_sell_above,
        sma_period=cfg.sma_trend_period,
    )
    log.info("Indicators for %s: price=$%.2f  %d-day-avg=$%.2f  RSI=%.1f",
             cfg.symbol, decision.price, cfg.sma_trend_period, decision.sma, decision.rsi)
    log.info("Strategy decision: %s", decision.reason)

    # --- (f + g) Risk-check the decision, then maybe act --------------
    if decision.action == Action.BUY:
        size = risk.buy_notional(snap, max_position_notional=cfg.max_position_notional)
        verdict = risk.check_buy_allowed(
            snap,
            intended_notional=size,
            max_position_notional=cfg.max_position_notional,
            account_floor=cfg.account_floor,
        )
        if not verdict.allowed:
            log.warning("Trade blocked by risk guardrails. %s", verdict.reason)
            return True
        log.info("Risk OK. %s", verdict.reason)
        order = execu.buy_notional(cfg.symbol, size)
        log.info("ORDER PLACED: BUY $%.2f of %s. (Alpaca order id: %s)",
                 size, cfg.symbol, getattr(order, "id", "n/a"))

    elif decision.action == Action.SELL:
        if not holding:
            log.info("Strategy said SELL but we hold none — nothing to sell.")
            return True
        order = execu.sell_all(cfg.symbol)
        log.info("ORDER PLACED: SELL all of %s. (Alpaca order id: %s)",
                 cfg.symbol, getattr(order, "id", "n/a"))

    else:  # HOLD
        log.info("No order placed this cycle.")

    # The market was open and we completed a full decision cycle today.
    return True


def prevent_system_sleep(log) -> None:
    """
    Ask Windows to stay awake while the bot runs.

    Plain English:
        An "always-on" trading bot is useless if the PC falls asleep, because
        a sleeping computer freezes the bot and it misses market hours. On
        Windows we tell the operating system "keep the system running while I'm
        alive." This lets the screen turn off (fine) but stops the machine from
        going to sleep on its own. It only lasts while the bot is running.
    """
    if os.name != "nt":
        return  # not Windows; nothing to do
    try:
        import ctypes
        ES_CONTINUOUS = 0x80000000
        ES_SYSTEM_REQUIRED = 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        log.info("Sleep prevention is ON: the PC will stay awake while the bot runs "
                 "(the screen may still turn off — that's fine).")
    except Exception as exc:
        log.warning("Could not enable sleep prevention (%s). If your PC sleeps, the "
                    "bot will pause and may miss market hours.", exc)


def main() -> None:
    cfg = load_config()
    log = setup_logger(cfg.logs_dir)

    mode = "PAPER (fake money)" if cfg.paper else "LIVE (REAL money)"
    log.info("Starting AI-Trader. Mode: %s. Symbol: %s.", mode, cfg.symbol)
    log.info("Guardrails: floor=$%.2f  max-position=$%.2f  max-daily-loss=$%.2f",
             cfg.account_floor, cfg.max_position_notional, cfg.max_daily_loss)

    # Keep the PC awake so an always-on bot doesn't sleep through market hours.
    prevent_system_sleep(log)

    # Refuse to start if another copy of the bot is already running, so two
    # copies can never trade the same account at once. Keep `lock` referenced
    # for the whole run; the OS frees it automatically when we exit.
    lock = acquire_single_instance_lock(cfg.lock_path)
    if lock is None:
        log.warning("Another AI-Trader instance is already running. "
                    "Exiting this copy to avoid double-trading. (This is a safety stop.)")
        return

    # THE SAFETY GATE: blocks (and may exit) if live trading isn't confirmed.
    confirm_live_trading_or_exit(cfg)

    # Build the broker connections ONCE and reuse them every cycle.
    feed = DataFeed(cfg.api_key, cfg.secret_key)
    execu = Execution(cfg.api_key, cfg.secret_key, paper=cfg.paper)

    # We remember the last calendar date we ACTED on, so we trade at most
    # about once per day even though we wake up hourly.
    last_action_date: str | None = None

    log.info("Entering main loop. Press Ctrl+C to stop. "
             "(Or create a file named '%s' to halt instantly.)", cfg.kill_switch_path)

    while True:
        try:
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            if last_action_date == today:
                log.info("Already ran a decision cycle today (%s). Waiting until "
                         "tomorrow. (Calm and simple, once a day.)", today)
            else:
                # run_once returns True only when the market was actually open,
                # so a weekend/holiday cycle doesn't "use up" the trading day.
                market_was_open = run_once(cfg, feed, execu, log)
                if market_was_open:
                    last_action_date = today

            # Sleep INSIDE the try so a Ctrl+C during the wait (where the bot
            # spends almost all of its time) is caught and handled cleanly.
            time.sleep(cfg.loop_interval_seconds)

        except KeyboardInterrupt:
            log.info("Ctrl+C received. Shutting down cleanly. Goodbye.")
            break
        except Exception as exc:  # never let one bad cycle kill the bot
            log.exception("A cycle hit an unexpected error (will retry next "
                          "wake-up): %s", exc)
            time.sleep(cfg.loop_interval_seconds)


if __name__ == "__main__":
    main()
