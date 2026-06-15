"""
risk.py  —  The guardrails. This module can VETO any trade.

Plain English:
    The strategy decides what it WANTS to do. The risk module decides what
    it is ALLOWED to do. Even a perfect-looking BUY signal gets blocked if
    it would break one of your hard money rules. Safety always wins.

The four non-negotiable guardrails (all configurable in your .env):

    1. KILL SWITCH
       If a file named KILL_SWITCH exists in the project folder, the bot
       does nothing at all. This is your big red "STOP EVERYTHING" button:
       create the file to halt, delete it to allow trading again.

    2. ACCOUNT_FLOOR  (default $35)
       If your total account value (equity) drops below this, halt ALL
       trading. This stops the bot from grinding a small account to zero.

    3. MAX_DAILY_LOSS  (default $10)
       If today's equity is down by this much from where it OPENED today,
       stop trading for the rest of the day. A bad day can't snowball.

    4. MAX_POSITION_NOTIONAL  (default $25)
       Never put more than this many dollars into the position. ("Notional"
       just means "dollar value of the position.") Caps the size of any
       single bet.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class RiskVerdict:
    allowed: bool        # True = the trade may proceed.
    reason: str          # Plain-English explanation for the log.
    halt_trading: bool = False   # True = a global halt (floor / daily loss / kill).


@dataclass
class AccountSnapshot:
    """A tiny snapshot of the account, passed in from the execution layer."""
    equity: float            # Total account value right now (cash + positions).
    last_equity: float       # Account value at the START of today.
    position_notional: float # Current dollar value we hold in our symbol (0 if none).


def kill_switch_active(kill_switch_path: str) -> bool:
    """The kill switch is ON if the control file exists on disk."""
    return os.path.exists(kill_switch_path)


def check_global_halts(
    account: AccountSnapshot,
    *,
    account_floor: float,
    max_daily_loss: float,
    kill_switch_path: str,
) -> RiskVerdict:
    """
    Checks that apply BEFORE we even look at a strategy decision. If any of
    these fire, the bot should not trade at all this cycle.
    """
    if kill_switch_active(kill_switch_path):
        return RiskVerdict(
            allowed=False, halt_trading=True,
            reason=(f"KILL SWITCH is ON (the file '{kill_switch_path}' exists). "
                    f"All trading halted. Delete that file to resume."),
        )

    if account.equity < account_floor:
        return RiskVerdict(
            allowed=False, halt_trading=True,
            reason=(f"ACCOUNT FLOOR breached: equity ${account.equity:.2f} is "
                    f"below the floor of ${account_floor:.2f}. Halting all "
                    f"trading to protect what's left."),
        )

    # How much are we down today, in dollars? (Positive number = a loss.)
    daily_loss = account.last_equity - account.equity
    if daily_loss >= max_daily_loss:
        return RiskVerdict(
            allowed=False, halt_trading=True,
            reason=(f"DAILY LOSS LIMIT hit: down ${daily_loss:.2f} from today's "
                    f"open (limit is ${max_daily_loss:.2f}). Stopping for today. "
                    f"Tomorrow is a fresh start."),
        )

    return RiskVerdict(allowed=True, reason="All global guardrails OK.")


def check_buy_allowed(
    account: AccountSnapshot,
    *,
    intended_notional: float,
    max_position_notional: float,
    account_floor: float,
) -> RiskVerdict:
    """
    Checks specific to placing a BUY order. Returns whether it's allowed and,
    if so, the caller already knows the dollar size to use.
    """
    # Don't add to a position that's already at/over the cap.
    if account.position_notional >= max_position_notional:
        return RiskVerdict(
            allowed=False,
            reason=(f"BUY vetoed: we already hold ${account.position_notional:.2f}, "
                    f"at or above the per-position cap of ${max_position_notional:.2f}."),
        )

    # Never spend so much that we'd drop the account below the floor.
    if account.equity - intended_notional < account_floor:
        return RiskVerdict(
            allowed=False,
            reason=(f"BUY vetoed: spending ${intended_notional:.2f} would push "
                    f"equity below the floor of ${account_floor:.2f}."),
        )

    return RiskVerdict(
        allowed=True,
        reason=(f"BUY allowed: investing ${intended_notional:.2f} "
                f"(within the ${max_position_notional:.2f} per-position cap)."),
    )


def buy_notional(
    account: AccountSnapshot,
    *,
    max_position_notional: float,
) -> float:
    """
    How many dollars to actually buy: the room left under the per-position
    cap. Usually this is the full cap (e.g. $25) on the first buy.
    """
    room = max_position_notional - account.position_notional
    return max(0.0, round(room, 2))
