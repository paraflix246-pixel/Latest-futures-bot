"""Regular-hours (RTH) helpers for US index futures.

RTH is the NYSE cash session 09:30–16:00 America/New_York. Overnight Globex
bars are still in the data; these helpers exist so strategies/engines can
opt into cash-hours-only entries and flatten before the equity close.

DST is handled by converting timestamps to America/New_York rather than
hard-coding a UTC offset.
"""
from __future__ import annotations

import pandas as pd

SESSION_TZ = "America/New_York"
RTH_START_MINUTES = 9 * 60 + 30  # 09:30
RTH_END_MINUTES = 16 * 60  # 16:00 exclusive


def _local_index(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    if index.tz is None:
        index = index.tz_localize("UTC")
    return index.tz_convert(SESSION_TZ)


def rth_mask(index: pd.DatetimeIndex) -> pd.Series:
    """True on bars whose *start* time is inside [09:30, 16:00) ET."""
    local = _local_index(index)
    minutes = local.hour * 60 + local.minute
    return pd.Series((minutes >= RTH_START_MINUTES) & (minutes < RTH_END_MINUTES), index=index)


def session_date(index: pd.DatetimeIndex) -> pd.Series:
    """Calendar date in America/New_York (the session date for RTH)."""
    local = _local_index(index)
    return pd.Series(local.date, index=index)


def last_rth_bar_mask(index: pd.DatetimeIndex) -> pd.Series:
    """True on the last RTH bar of each session (timeframe-agnostic)."""
    mask = rth_mask(index)
    nxt = mask.shift(-1, fill_value=False)
    return mask & ~nxt


def minutes_since_rth_open(index: pd.DatetimeIndex) -> pd.Series:
    """Minutes from 09:30 ET to the bar start. Negative before the cash open."""
    local = _local_index(index)
    minutes = local.hour * 60 + local.minute
    return pd.Series(minutes - RTH_START_MINUTES, index=index)


def minutes_of_day(index: pd.DatetimeIndex) -> pd.Series:
    """Minutes since local midnight in America/New_York for each bar start."""
    local = _local_index(index)
    return pd.Series(local.hour * 60 + local.minute, index=index)


def local_minutes(ts: pd.Timestamp) -> int:
    """Minutes since midnight in America/New_York for one timestamp."""
    if ts.tzinfo is None:
        ts = pd.Timestamp(ts).tz_localize("UTC")
    else:
        ts = pd.Timestamp(ts)
    local = ts.tz_convert(SESSION_TZ)
    return int(local.hour * 60 + local.minute)
