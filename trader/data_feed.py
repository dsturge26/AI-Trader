"""
data_feed.py  —  Gets price history from Alpaca.

Plain English:
    Before the bot can decide anything, it needs to know how the stock has
    been priced recently. This module asks Alpaca for the last several
    months of DAILY price "bars" and hands them back as a simple table.

    A "bar" is one day's summary of a stock's price: where it Opened, the
    High and Low it reached, and where it Closed. We mostly care about the
    CLOSE price (the final price of the day), because that's the number our
    indicators are built on.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame


class DataFeed:
    """Thin wrapper around Alpaca's historical-data client for daily bars."""

    def __init__(self, api_key: str, secret_key: str):
        # The data client is the same for paper and live — price data is
        # public market data, not tied to your fake/real money account.
        self._client = StockHistoricalDataClient(api_key, secret_key)

    def get_daily_bars(self, symbol: str, lookback_days: int = 200) -> pd.DataFrame:
        """
        Fetch roughly `lookback_days` calendar days of DAILY bars for `symbol`.

        Returns a pandas DataFrame (a table) with columns including 'close',
        indexed by date, oldest first. We grab extra calendar days because
        markets are closed on weekends/holidays, so calendar days > trading
        days. The strategy needs enough rows to compute a 50-day average.
        """
        # Alpaca's free data has a ~15 minute delay and won't return *today's*
        # not-yet-finished bar, which is fine: we trade on COMPLETED daily bars.
        end = datetime.now(timezone.utc) - timedelta(minutes=20)
        start = end - timedelta(days=lookback_days)

        request = StockBarsRequest(
            symbol_or_symbols=[symbol],
            timeframe=TimeFrame.Day,
            start=start,
            end=end,
        )

        bars = self._client.get_stock_bars(request)
        df = bars.df  # Multi-indexed by (symbol, timestamp).

        if df is None or df.empty:
            raise RuntimeError(
                f"No price data returned for '{symbol}'. "
                f"Check the symbol is valid and your API keys work."
            )

        # The frame is indexed by (symbol, timestamp). Pull out our one symbol
        # and keep just the timestamp as the index.
        df = df.loc[symbol].copy()
        df.sort_index(inplace=True)  # oldest first
        return df

    def latest_close(self, df: pd.DataFrame) -> float:
        """The most recent completed daily closing price."""
        return float(df["close"].iloc[-1])
