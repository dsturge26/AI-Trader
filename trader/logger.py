"""
logger.py  —  Writes everything the bot does, in plain English.

Plain English:
    Every time the bot makes a decision (buy / sell / hold) or hits a
    guardrail, it writes a sentence here. The sentences go to BOTH:
      1. your screen, and
      2. a file under logs/  (one file per day),
    so you can always read back exactly what the bot did and WHY.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler


def setup_logger(log_dir: str = "logs") -> logging.Logger:
    """Create a logger that prints to the screen and appends to a daily file."""
    os.makedirs(log_dir, exist_ok=True)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    log_path = os.path.join(log_dir, f"trader-{today}.log")

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

    # 2) To a file (rotates if it ever gets huge, keeping a few backups).
    file_handler = RotatingFileHandler(
        log_path, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
    )
    file_handler.setFormatter(fmt)
    logger.addHandler(file_handler)

    logger.info("=" * 70)
    logger.info("AI-Trader logger started. Writing to %s", log_path)
    return logger
