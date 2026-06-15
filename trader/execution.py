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

from alpaca.trading.client import TradingClient
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.trading.requests import MarketOrderRequest

from .risk import AccountSnapshot


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
