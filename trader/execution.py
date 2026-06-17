"""
execution.py  —  The only module that actually places orders.

Plain English:
    This is the bot's "hands." Everything else just thinks and decides;
    this module is the only place that connects to your Alpaca account,
    reads your balance, and submits real buy/sell orders. Keeping all the
    money-touching code in one file makes it easy to audit and trust.

    We use "market orders," which means "buy/sell at the best price
    available right now." We use "notional" orders, which means "buy $25
    worth" rather than "buy 3 shares" — Alpaca figures out the fractional
    share count for us. This keeps position sizing simple and precise.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from .risk import AccountSnapshot


@dataclass
class OpenPosition:
    """A single position we currently hold, with the few numbers the
    day-trader needs to manage it."""
    symbol: str
    qty: float
    market_value: float        # current dollar value of the position
    unrealized_plpc: float     # unrealized profit/loss as a FRACTION (0.05 = +5%)
    current_price: float


class Execution:
    """Wraps Alpaca's TradingClient. Paper vs live is decided by `paper`."""

    def __init__(self, api_key: str, secret_key: str, *, paper: bool):
        # paper=True -> orders hit the fake-money paper endpoint.
        # paper=False -> orders hit the REAL-money live endpoint.
        self._client = TradingClient(api_key, secret_key, paper=paper)
        self.paper = paper

    # ---- Reading the account ------------------------------------------

    def market_is_open(self) -> bool:
        """True if the US stock market is currently open for trading."""
        return bool(self._client.get_clock().is_open)

    def position_notional(self, symbol: str) -> float:
        """Current dollar value we hold in `symbol` (0.0 if we hold none)."""
        for pos in self._client.get_all_positions():
            if pos.symbol == symbol:
                return abs(float(pos.market_value))
        return 0.0

    def holding(self, symbol: str) -> bool:
        """True if we currently own any of `symbol`."""
        return self.position_notional(symbol) > 0.0

    def snapshot(self, symbol: str) -> AccountSnapshot:
        """Gather the few account numbers the risk module needs to decide."""
        account = self._client.get_account()
        return AccountSnapshot(
            equity=float(account.equity),
            last_equity=float(account.last_equity),
            position_notional=self.position_notional(symbol),
        )

    def account_snapshot(self) -> AccountSnapshot:
        """
        Like snapshot(), but for the day-trader, which holds MANY symbols at
        once. `position_notional` here is the TOTAL dollar value across every
        open position (the global guardrails only care about account totals).
        """
        account = self._client.get_account()
        total = sum(abs(float(p.market_value)) for p in self._client.get_all_positions())
        return AccountSnapshot(
            equity=float(account.equity),
            last_equity=float(account.last_equity),
            position_notional=total,
        )

    def list_positions(self) -> list[OpenPosition]:
        """Every position we currently hold, as simple OpenPosition records."""
        out: list[OpenPosition] = []
        for p in self._client.get_all_positions():
            out.append(OpenPosition(
                symbol=p.symbol,
                qty=float(p.qty),
                market_value=abs(float(p.market_value)),
                unrealized_plpc=float(p.unrealized_plpc),
                current_price=float(p.current_price),
            ))
        return out

    def buying_power(self) -> float:
        """Cash available to open new positions right now."""
        return float(self._client.get_account().buying_power)

    def minutes_to_close(self) -> float:
        """
        Minutes until the market closes today (0.0 if it's already closed).
        Used to flatten day-trades before the bell so nothing is held overnight.
        """
        clock = self._client.get_clock()
        if not clock.is_open:
            return 0.0
        now = clock.timestamp or datetime.now(timezone.utc)
        return max(0.0, (clock.next_close - now).total_seconds() / 60.0)

    # ---- Placing orders -----------------------------------------------

    def buy_notional(self, symbol: str, notional: float):
        """Buy approximately `notional` dollars' worth of `symbol`."""
        order = MarketOrderRequest(
            symbol=symbol,
            notional=round(notional, 2),
            side=OrderSide.BUY,
            time_in_force=TimeInForce.DAY,  # required for notional/fractional
        )
        return self._client.submit_order(order_data=order)

    def sell_all(self, symbol: str):
        """Sell our entire position in `symbol` (a full exit)."""
        # close_position liquidates the whole position with one call.
        return self._client.close_position(symbol)
