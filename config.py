"""
config.py  —  One place for every setting the bot uses.

Plain English:
    This file reads your .env file and turns it into simple Python values
    that the rest of the program can use. It also contains the SAFETY GATE
    that decides whether we are allowed to use real money.

Nothing in here places a trade. It only reads settings and validates them.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# The project's root folder = the folder this file lives in. We anchor every
# file path (the .env, the logs folder, the kill switch) to THIS, so the bot
# works no matter what folder it's launched from. (Windows Task Scheduler, for
# example, starts programs in C:\Windows\System32 — without this, the bot
# couldn't find its own .env file and would exit instantly.)
PROJECT_ROOT = Path(__file__).resolve().parent

# Read the .env file (using its absolute path) into the environment.
load_dotenv(PROJECT_ROOT / ".env")


def _get(name: str, default: str | None = None) -> str:
    """Read a setting, falling back to a default. Error out if required and missing."""
    value = os.getenv(name, default)
    if value is None:
        print(f"[CONFIG ERROR] Missing required setting '{name}'. "
              f"Did you copy .env.example to .env and fill it in?")
        sys.exit(1)
    return value


def _get_float(name: str, default: str) -> float:
    raw = _get(name, default)
    try:
        return float(raw)
    except ValueError:
        print(f"[CONFIG ERROR] Setting '{name}={raw}' is not a number.")
        sys.exit(1)


def _get_int(name: str, default: str) -> int:
    return int(_get_float(name, default))


def _get_bool(name: str, default: str) -> bool:
    """Treat 'true', '1', 'yes', 'on' (any case) as True; everything else False."""
    return _get(name, default).strip().lower() in ("true", "1", "yes", "on")


def _get_list(name: str, default: str) -> list[str]:
    """Read a comma-separated setting into a clean list of UPPERCASE symbols."""
    raw = _get(name, default)
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


@dataclass
class Config:
    """All the bot's settings, grouped in one tidy object."""

    # --- Brokerage credentials ---
    api_key: str
    secret_key: str
    paper: bool          # True = fake money (safe). False = REAL money.

    # --- Which brain to use: "swing" (buy dips, once a day) or
    #     "momentum" (day-trade today's biggest gainers) ---
    strategy: str

    # --- What to trade (swing mode only; momentum scans the whole market) ---
    symbol: str

    # --- Hard money guardrails (dollars) ---
    account_floor: float
    max_position_notional: float
    max_daily_loss: float

    # --- Swing-strategy knobs ---
    sma_trend_period: int
    rsi_period: int
    rsi_buy_below: float
    rsi_sell_above: float

    # --- Momentum (day-trader) knobs ---
    take_profit_pct: float            # sell a winner once it's up this %
    stop_loss_pct: float              # sell a loser once it's down this %
    max_open_positions: int           # how many movers to hold at once
    min_gainer_pct: float             # ignore movers smaller than this
    max_gainer_pct: float             # ignore movers bigger than this (skip mania)
    min_price: float                  # ignore stocks cheaper than this (penny junk)
    scan_top: int                     # how many top movers to pull from the feed
    flatten_minutes_before_close: float  # sell everything this long before close
    watchlist: list[str]              # fallback tickers if the movers feed is off

    # --- Loop timing ---
    loop_interval_seconds: int

    # --- Local file locations (absolute, anchored to the project folder) ---
    kill_switch_path: str = str(PROJECT_ROOT / "KILL_SWITCH")
    logs_dir: str = str(PROJECT_ROOT / "logs")
    lock_path: str = str(PROJECT_ROOT / "bot.lock")


def load_config() -> Config:
    """Build a Config object from the environment / .env file."""
    return Config(
        api_key=_get("ALPACA_API_KEY"),
        secret_key=_get("ALPACA_SECRET_KEY"),
        paper=_get_bool("ALPACA_PAPER", "true"),
        strategy=_get("STRATEGY", "swing").strip().lower(),
        symbol=_get("SYMBOL", "SPY").upper().strip(),
        account_floor=_get_float("ACCOUNT_FLOOR", "35"),
        max_position_notional=_get_float("MAX_POSITION_NOTIONAL", "25"),
        max_daily_loss=_get_float("MAX_DAILY_LOSS", "10"),
        sma_trend_period=_get_int("SMA_TREND_PERIOD", "50"),
        rsi_period=_get_int("RSI_PERIOD", "14"),
        rsi_buy_below=_get_float("RSI_BUY_BELOW", "35"),
        rsi_sell_above=_get_float("RSI_SELL_ABOVE", "70"),
        take_profit_pct=_get_float("TAKE_PROFIT_PCT", "10"),
        stop_loss_pct=_get_float("STOP_LOSS_PCT", "5"),
        max_open_positions=_get_int("MAX_OPEN_POSITIONS", "5"),
        min_gainer_pct=_get_float("MIN_GAINER_PCT", "5"),
        max_gainer_pct=_get_float("MAX_GAINER_PCT", "1000"),
        min_price=_get_float("MIN_PRICE", "2"),
        scan_top=_get_int("SCAN_TOP", "50"),
        flatten_minutes_before_close=_get_float("FLATTEN_MINUTES_BEFORE_CLOSE", "10"),
        watchlist=_get_list("WATCHLIST", ""),
        loop_interval_seconds=_get_int("LOOP_INTERVAL_SECONDS", "900"),
    )


def confirm_live_trading_or_exit(cfg: Config) -> None:
    """
    THE SAFETY GATE.

    If the user has set ALPACA_PAPER=false (REAL money), we refuse to
    continue until they read a loud warning and type an explicit phrase.
    This function NEVER flips anything to live on its own — it only blocks.
    """
    if cfg.paper:
        # Fake money. Nothing to confirm — this is the safe path.
        return

    warning = r"""
    ##################################################################
    #                                                                #
    #   !!!  LIVE TRADING IS ENABLED  —  THIS USES REAL MONEY  !!!    #
    #                                                                #
    #   ALPACA_PAPER is set to FALSE. Every order the bot places     #
    #   will spend or sell REAL dollars in your Alpaca account.      #
    #                                                                #
    #   If you did not mean to do this, press Ctrl+C NOW and set     #
    #   ALPACA_PAPER=true in your .env file.                         #
    #                                                                #
    ##################################################################
    """
    print(warning, flush=True)

    # Require an exact phrase. A simple "y" is too easy to fat-finger.
    required = "USE REAL MONEY"
    try:
        answer = input(f'Type exactly  {required}  to proceed (anything else aborts): ')
    except EOFError:
        # No interactive terminal (e.g. running as a background service).
        # Fail safe: refuse to trade real money without a human present.
        print("[SAFETY] No interactive terminal to confirm live trading. Aborting.")
        sys.exit(1)

    if answer.strip() != required:
        print("[SAFETY] Confirmation not given. Aborting. (Good — staying safe.)")
        sys.exit(1)

    print("[SAFETY] Live trading confirmed by user. Proceeding with REAL money.\n")
