"""
logger.py  —  Writes everything the bot does, in plain English.

Plain English:
    Every time the bot makes a decision (buy / sell / hold) or hits a
    guardrail, it writes a sentence here. The sentences go to BOTH:
      1. your screen, and
      2. a file under logs/  (one file per day),
    so you can always read back exactly what the bot did and WHY.

    The log file is named for the day, e.g. logs/trader-2026-06-16.log.
    Because the bot can run for many days without stopping, the file handler
    below AUTOMATICALLY switches to a new dated file when the calendar date
    changes (just after midnight) — so you always get one tidy file per day,
    not one giant file named for the day you happened to start it.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime


class DailyDateFileHandler(logging.FileHandler):
    """
    Like a normal file handler, but it writes to logs/trader-<today>.log and,
    if the date rolls over while the bot is running, it quietly closes the old
    file and opens a fresh one for the new day. No restart needed.
    """

    def __init__(self, log_dir: str):
        self._log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        self._current_date = self._today()
        super().__init__(self._path_for(self._current_date), encoding="utf-8")

    @staticmethod
    def _today() -> str:
        # Local date, to match the local timestamps shown on each log line.
        return datetime.now().strftime("%Y-%m-%d")

    def _path_for(self, date_str: str) -> str:
        return os.path.join(self._log_dir, f"trader-{date_str}.log")

    def emit(self, record: logging.LogRecord) -> None:
        today = self._today()
        if today != self._current_date:
            # Date changed -> switch to the new day's file.
            self.close()
            self._current_date = today
            self.baseFilename = os.path.abspath(self._path_for(today))
            self.stream = self._open()
        super().emit(record)


def setup_logger(log_dir: str = "logs") -> logging.Logger:
    """Create a logger that prints to the screen and appends to a daily file."""
    os.makedirs(log_dir, exist_ok=True)

    logger = logging.getLogger("ai-trader")
    logger.setLevel(logging.INFO)

    # If this function is called twice, don't add duplicate handlers.
    if logger.handlers:
        return logger

    # Human-readable format: time, level, then the plain-English message.
    fmt = logging.Formatter(
        fmt="%(asctime)s  %(levelname)-7s  %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1) To the screen.
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(console)

    # 2) To a dated file that rolls over automatically at midnight.
    file_handler = DailyDateFileHandler(log_dir)
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.info("=" * 70)
    logger.info("AI-Trader logger started. Writing to %s", file_handler.baseFilename)
    return logger
