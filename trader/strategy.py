"""
strategy.py  —  The bot's "brain": indicators in, decision out.

This is the ONLY place the buy/sell/hold rule lives. It does not touch
money or place orders — it just returns a decision plus a plain-English
reason. The execution and risk modules handle the rest.

==========================================================================
THE STRATEGY, IN ONE PARAGRAPH
==========================================================================
We only ever BUY a stock that is in a healthy uptrend but has TEMPORARILY
dipped (gotten a bit cheap). We SELL when it has run up and gotten
expensive, OR when the uptrend itself breaks. This is a well-known,
conservative beginner idea often called "buy the dip in an uptrend." It is
deliberately calm: most days it will do NOTHING ("hold"), which is normal
and good.

==========================================================================
THE EXACT RULES
==========================================================================
Let:
    price = the latest daily closing price
    sma   = the 50-day simple moving average (our "trend line")
    rsi   = the 14-day RSI (our 0-100 cheap/expensive meter)

We are in an UPTREND when:  price > sma
We are in a DOWNTREND when: price < sma

BUY (only if we currently hold NONE of the stock) when ALL are true:
    - price > sma           (trend is up = the stock is generally healthy)
    - rsi   < RSI_BUY_BELOW  (e.g. < 35 = it just dipped / looks cheap)
  -> Translation: "A healthy stock went on temporary sale. Buy some."

SELL (only if we currently HOLD the stock) when EITHER is true:
    - rsi   > RSI_SELL_ABOVE (e.g. > 70 = it got expensive; take profit)
    - price < sma            (the uptrend broke; protect ourselves, get out)
  -> Translation: "Either it got pricey, or it's no longer healthy. Exit."

HOLD (do nothing) in every other case. This will be most days.
==========================================================================
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import pandas as pd


class Action(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class Decision:
    action: Action
    reason: str          # Plain-English explanation, for the logs.
    price: float
    sma: float
    rsi: float


def decide(
    df_with_indicators: pd.DataFrame,
    *,
    holding: bool,
    rsi_buy_below: float,
    rsi_sell_above: float,
    sma_period: int = 50,
) -> Decision:
    """
    Look at the most recent row of indicators and return a Decision.

    `holding` is True if we currently own a position in this stock, which
    matters because you can only sell something you own, and we don't want
    to pile more into a position we already have.
    """
    last = df_with_indicators.iloc[-1]
    price = float(last["close"])
    sma = float(last["sma"])
    rsi = float(last["rsi"])

    # Guard: if we don't yet have enough history, the SMA/RSI will be NaN
    # (Not a Number). In that case we must not act — we hold and say so.
    if pd.isna(sma) or pd.isna(rsi):
        return Decision(
            action=Action.HOLD,
            reason=("Not enough price history yet to compute the indicators "
                    "(need more days). Holding to stay safe."),
            price=price, sma=sma, rsi=rsi,
        )

    uptrend = price > sma
    trend_word = (f"UPTREND (price above its {sma_period}-day average)" if uptrend
                  else f"DOWNTREND (price below its {sma_period}-day average)")

    if holding:
        # We own it. Look for a reason to SELL; otherwise hold.
        if rsi > rsi_sell_above:
            return Decision(
                action=Action.SELL,
                reason=(f"SELL: We own it and RSI is {rsi:.1f}, above the "
                        f"'expensive' line of {rsi_sell_above:.0f}. The price "
                        f"ran up fast, so we take our gains and step aside."),
                price=price, sma=sma, rsi=rsi,
            )
        if not uptrend:
            return Decision(
                action=Action.SELL,
                reason=(f"SELL: We own it but the price ({price:.2f}) fell "
                        f"below its {sma_period}-day average ({sma:.2f}). The "
                        f"healthy uptrend broke, so we exit to protect ourselves."),
                price=price, sma=sma, rsi=rsi,
            )
        return Decision(
            action=Action.HOLD,
            reason=(f"HOLD: We own it and things look fine. {trend_word}; "
                    f"RSI is {rsi:.1f} (not yet above {rsi_sell_above:.0f}). "
                    f"Nothing to do — letting the winner run."),
            price=price, sma=sma, rsi=rsi,
        )

    # We do NOT own it. Look for a reason to BUY; otherwise hold.
    if uptrend and rsi < rsi_buy_below:
        return Decision(
            action=Action.BUY,
            reason=(f"BUY: The stock is in an {trend_word}, AND RSI is "
                    f"{rsi:.1f}, below the 'cheap' line of {rsi_buy_below:.0f}. "
                    f"A healthy stock just dipped — that's our entry."),
            price=price, sma=sma, rsi=rsi,
        )

    # Explain WHY we're not buying, so the log is genuinely useful.
    if not uptrend:
        why = (f"HOLD: Not buying because the stock is in a {trend_word}. "
               f"We only buy stocks that are trending up.")
    else:
        why = (f"HOLD: The stock is healthy ({trend_word}) but RSI is "
               f"{rsi:.1f}, not below the 'cheap' line of {rsi_buy_below:.0f}. "
               f"It hasn't dipped enough to be a bargain yet. Waiting.")

    return Decision(action=Action.HOLD, reason=why, price=price, sma=sma, rsi=rsi)
