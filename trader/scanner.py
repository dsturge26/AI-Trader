"""
scanner.py  —  Finds the stocks that are PUMPING today (the day-trader's radar).

Plain English:
    The swing strategy watches ONE stock and waits for it to dip. A day-trader
    needs the opposite: scan the WHOLE market and find the handful of stocks
    shooting UP right now, then ride that momentum for a few minutes or hours.

    Alpaca has a built-in "market movers" feed that hands back the day's biggest
    gainers directly, so we don't have to download thousands of tickers and rank
    them ourselves. That feed is this module's primary source.

    If your Alpaca data plan doesn't expose the movers feed, we fall back to a
    WATCHLIST you set in .env: a comma-separated list of tickers we measure by
    hand (how far each has moved since today's opening price). The fallback only
    sees the stocks you list — it can't discover surprises — but it keeps the bot
    working instead of going dark.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Candidate:
    """One stock that's a possible buy: how much it's up today and its price."""
    symbol: str
    percent_change: float   # today's move, e.g. 12.5 means +12.5%
    price: float


class Scanner:
    """Wraps Alpaca's market-movers feed, with a WATCHLIST fallback."""

    def __init__(self, api_key: str, secret_key: str, *, watchlist: list[str] | None = None):
        self._api_key = api_key
        self._secret_key = secret_key
        self._watchlist = watchlist or []
        # The Alpaca clients are created lazily (only when first needed) so a
        # missing/old SDK doesn't stop the whole bot from importing.
        self._screener = None
        self._data = None

    # ---- The main job: today's filtered top gainers --------------------

    def top_gainers(
        self,
        *,
        top: int,
        min_change_pct: float,
        max_change_pct: float,
        min_price: float,
        log,
    ) -> list[Candidate]:
        """
        Return today's biggest gainers that pass our sanity filters, strongest
        first. We filter so the bot doesn't chase illiquid penny stocks or, in
        the conservative profiles, ignore tiny moves.
        """
        raw, source = self._raw_gainers(top=top, log=log)

        kept = [
            c for c in raw
            if c.price >= min_price and min_change_pct <= c.percent_change <= max_change_pct
        ]
        kept.sort(key=lambda c: c.percent_change, reverse=True)

        log.info(
            "Scan (%s): %d gainers seen, %d pass filters "
            "(move %+.0f%%..%+.0f%%, price >= $%.2f).",
            source, len(raw), len(kept), min_change_pct, max_change_pct, min_price,
        )
        if kept:
            preview = ", ".join(f"{c.symbol} {c.percent_change:+.1f}%" for c in kept[:5])
            log.info("Top candidates: %s", preview)
        return kept

    # ---- Source 1: Alpaca's market-movers feed -------------------------

    def _raw_gainers(self, *, top: int, log) -> tuple[list[Candidate], str]:
        """Try the movers feed; on any failure, fall back to the watchlist."""
        try:
            from alpaca.data.historical.screener import ScreenerClient
            from alpaca.data.requests import MarketMoversRequest

            if self._screener is None:
                self._screener = ScreenerClient(self._api_key, self._secret_key)

            movers = self._screener.get_market_movers(MarketMoversRequest(top=top))
            raw = [
                Candidate(m.symbol, float(m.percent_change), float(m.price))
                for m in movers.gainers
            ]
            return raw, "Alpaca market-movers feed"
        except Exception as exc:  # noqa: BLE001 - we WANT to degrade gracefully
            if self._watchlist:
                log.warning(
                    "Market-movers feed unavailable (%s). Falling back to your "
                    "WATCHLIST of %d tickers.", exc, len(self._watchlist),
                )
                return self._watchlist_gainers(log), "WATCHLIST fallback"
            log.warning(
                "Market-movers feed unavailable (%s) and no WATCHLIST is set, so "
                "the scanner has nothing to look at. Set WATCHLIST=SYM1,SYM2,... in "
                ".env to scan a custom list. Holding for now.", exc,
            )
            return [], "no source"

    # ---- Source 2: a hand-measured WATCHLIST ---------------------------

    def _watchlist_gainers(self, log) -> list[Candidate]:
        """Measure each watchlist symbol's move since today's open via a snapshot."""
        try:
            from alpaca.data.historical import StockHistoricalDataClient
            from alpaca.data.requests import StockSnapshotRequest

            if self._data is None:
                self._data = StockHistoricalDataClient(self._api_key, self._secret_key)

            snaps = self._data.get_stock_snapshot(
                StockSnapshotRequest(symbol_or_symbols=self._watchlist)
            )
        except Exception as exc:  # noqa: BLE001
            log.warning("Could not read watchlist snapshots (%s).", exc)
            return []

        out: list[Candidate] = []
        for sym, snap in snaps.items():
            try:
                open_px = float(snap.daily_bar.open)
                last_px = float(snap.latest_trade.price)
                if open_px > 0:
                    pct = (last_px - open_px) / open_px * 100.0
                    out.append(Candidate(sym, pct, last_px))
            except Exception:  # noqa: BLE001 - skip any symbol with missing data
                continue
        return out
