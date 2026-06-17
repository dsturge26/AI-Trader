"""
momentum.py  —  The day-trader's brain: when to bail, and what to chase.

Plain English:
    This is the day-trading counterpart to strategy.py. Where strategy.py buys
    DIPS and holds for the long run, this module buys PUMPS (stocks shooting up
    today) and gets out fast — taking a quick profit, cutting a loss, or
    flattening before the closing bell so nothing is held overnight.

    Like strategy.py, this file only THINKS. It never touches your account.
    main.py feeds it numbers and acts on the answers. Keeping the decision logic
    pure like this makes it easy to read, trust, and verify.
"""

from __future__ import annotations

from dataclasses import dataclass

from .scanner import Candidate


@dataclass
class ExitDecision:
    sell: bool
    reason: str


def should_exit(
    *,
    symbol: str,
    unrealized_plpc: float,   # Alpaca gives a FRACTION, e.g. 0.05 = +5%
    take_profit_pct: float,
    stop_loss_pct: float,
    force_flatten: bool,
) -> ExitDecision:
    """
    Decide whether to sell an open day-trade position.

    Three reasons to exit, in priority order:
        1. force_flatten — the market is about to close; never hold overnight.
        2. take-profit  — we're up enough; lock in the gain.
        3. stop-loss    — we're down too much; cut it before it gets worse.
    Otherwise we hold and let the trade breathe.
    """
    pct = unrealized_plpc * 100.0  # convert fraction -> human percent

    if force_flatten:
        return ExitDecision(
            True,
            f"SELL {symbol}: market is about to close — flattening so we hold "
            f"nothing overnight (P&L {pct:+.1f}%).",
        )
    if pct >= take_profit_pct:
        return ExitDecision(
            True,
            f"SELL {symbol}: hit the +{take_profit_pct:.0f}% take-profit "
            f"(now {pct:+.1f}%). Banking the win.",
        )
    if pct <= -stop_loss_pct:
        return ExitDecision(
            True,
            f"SELL {symbol}: hit the -{stop_loss_pct:.0f}% stop-loss "
            f"(now {pct:+.1f}%). Cutting the loss before it grows.",
        )
    return ExitDecision(
        False,
        f"HOLD {symbol}: P&L {pct:+.1f}% — still between the -{stop_loss_pct:.0f}% "
        f"stop and the +{take_profit_pct:.0f}% target. Letting it run.",
    )


def pick_buys(
    candidates: list[Candidate],
    *,
    exclude_symbols: set[str],
    open_count: int,
    max_positions: int,
) -> list[Candidate]:
    """
    Choose which pumps to buy THIS cycle.

    We take the strongest gainers we don't already hold (and didn't just sell),
    but only enough to fill the free slots under the max-positions cap. The
    `candidates` list is assumed already sorted strongest-first by the scanner.
    """
    free = max(0, max_positions - open_count)
    picks: list[Candidate] = []
    for c in candidates:
        if free <= 0:
            break
        if c.symbol in exclude_symbols:
            continue
        picks.append(c)
        free -= 1
    return picks
