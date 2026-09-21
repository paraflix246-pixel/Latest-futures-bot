"""Fixed-fractional position sizing driven by stop distance and account risk."""
from __future__ import annotations

import math

from src.instruments.instrument_registry import InstrumentSpec


def contracts_for_risk(
    account_size: float,
    risk_pct: float,
    entry: float,
    stop: float,
    spec: InstrumentSpec,
    max_contracts: int | None = None,
) -> int:
    """Number of contracts such that a stop-out loses ~risk_pct% of account_size.

    Returns 0 if even a single contract's stop-loss would exceed the risk budget.
    `max_contracts` caps size so a tight stop cannot request an implausible
    number of contracts (a 2-tick stop on MNQ is $1 of risk; uncapped 0.5% of
    $50k would be 250 contracts).
    """
    dollar_risk_budget = account_size * (risk_pct / 100.0)
    ticks_at_risk = abs(entry - stop) / spec.tick_size
    if ticks_at_risk <= 0:
        return 0
    dollar_risk_per_contract = ticks_at_risk * spec.tick_value_usd
    if dollar_risk_per_contract <= 0:
        return 0
    n = max(0, math.floor(dollar_risk_budget / dollar_risk_per_contract))
    if max_contracts is not None:
        n = min(n, max_contracts)
    return n
