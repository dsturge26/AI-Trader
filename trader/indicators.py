"""
indicators.py  —  Turns raw prices into two simple "signals".

This module computes the two indicators our strategy uses. An "indicator"
is just a number calculated from past prices that summarizes something
useful. We compute them by hand (with pandas) so nothing is a black box.

--------------------------------------------------------------------------
1) SMA  =  Simple Moving Average
--------------------------------------------------------------------------
Plain English:
    Take the closing price of the last N days and average them. Tomorrow,
    drop the oldest day and add the newest — the average "moves" along.

Everyday analogy:
    Imagine tracking your weight every morning. One day's number is noisy
    (you drank a lot of water). But the AVERAGE of the last 50 mornings
    tells you the real TREND — are you slowly going up or down? That's a
    moving average for a stock price.

We use it as a TREND filter:
    If today's price is ABOVE its 50-day average, the stock is generally
    trending UP (healthy). If it's BELOW, it's trending DOWN (weak).

--------------------------------------------------------------------------
2) RSI  =  Relative Strength Index   (a 0-to-100 "cheap vs expensive" meter)
--------------------------------------------------------------------------
Plain English:
    RSI looks at the last 14 days and measures how much of the recent move
    was UP versus DOWN. It produces a number from 0 to 100:
        - Near 70+  -> the price has risen a lot quickly = "overbought"
                       (think: ran up fast, maybe due for a breather).
        - Near 30-  -> the price has fallen a lot quickly = "oversold"
                       (think: beaten down, maybe temporarily too cheap).
        - Around 50 -> nothing extreme going on.

Everyday analogy:
    Think of RSI as a "how stretched is the rubber band?" meter. Pull a
    rubber band far in one direction (a big fast move) and it tends to snap
    back. High RSI = stretched up. Low RSI = stretched down.

IMPORTANT honesty note:
    These indicators do NOT predict the future. They only describe what has
    already happened. No indicator is ever guaranteed to be right — which is
    exactly why the risk module (the guardrails) exists.
"""

from __future__ import annotations

import pandas as pd


def simple_moving_average(closes: pd.Series, period: int) -> pd.Series:
    """Average of the last `period` closing prices, for every day."""
    return closes.rolling(window=period, min_periods=period).mean()


def relative_strength_index(closes: pd.Series, period: int = 14) -> pd.Series:
    """
    Classic Wilder's RSI.

    How it works (in steps):
      1. Day-to-day change = today's close minus yesterday's close.
      2. Split changes into "gains" (up days) and "losses" (down days).
      3. Smooth the average gain and average loss over `period` days.
      4. RS = average gain / average loss.
      5. RSI = 100 - (100 / (1 + RS)), which squashes RS into a 0-100 range.
    """
    delta = closes.diff()

    gains = delta.clip(lower=0.0)            # keep ups, zero out downs
    losses = -delta.clip(upper=0.0)         # keep downs (as positives)

    # Wilder's smoothing is an exponential-ish moving average.
    avg_gain = gains.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = losses.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    # If there were zero losses, avg_loss is 0 -> rs is infinite -> RSI = 100.
    rsi = rsi.fillna(100.0)
    return rsi


def compute_indicators(df: pd.DataFrame, sma_period: int, rsi_period: int) -> pd.DataFrame:
    """
    Add 'sma' and 'rsi' columns to a copy of the price table and return it.
    The last row holds the most recent values the strategy will look at.
    """
    out = df.copy()
    out["sma"] = simple_moving_average(out["close"], sma_period)
    out["rsi"] = relative_strength_index(out["close"], rsi_period)
    return out
