"""RTH session helpers shared by the new intra-session strategies.

CME equity-index RTH is treated as 09:30–16:00 America/New_York (cash open
to cash close). Strategies in this package trade that window only and the
engine flattens at the cash close so nothing is held overnight.
"""
from __future__ import annotations

from typing import Tuple

import pandas as pd

SESSION_TZ = "America/New_York"
RTH_OPEN_MINUTES = 9 * 60 + 30
RTH_CLOSE_MINUTES = 16 * 60
# Last time a new entry is allowed when flatten-at-close is on. Leaves a
# 30-minute buffer so a trade is not opened and immediately flattened.
RTH_ENTRY_CUTOFF_MINUTES = 15 * 60 + 30


def to_session_index(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    """Convert a DatetimeIndex to America/New_York. Naive stamps are UTC."""
    if index.tz is None:
        return index.tz_localize("UTC").tz_convert(SESSION_TZ)
    return index.tz_convert(SESSION_TZ)


def session_clock(index: pd.DatetimeIndex) -> Tuple[pd.Series, pd.Series]:
    """Return (minutes_of_day, session_date) in America/New_York."""
    local = to_session_index(index)
    minutes = pd.Series(local.hour * 60 + local.minute, index=index)
    dates = pd.Series(local.date, index=index)
    return minutes, dates


def local_minutes(ts: pd.Timestamp) -> int:
    """Minutes since midnight in America/New_York for one timestamp."""
    if ts.tzinfo is None:
        ts = pd.Timestamp(ts).tz_localize("UTC")
    else:
        ts = pd.Timestamp(ts)
    local = ts.tz_convert(SESSION_TZ)
    return int(local.hour * 60 + local.minute)


def in_rth_entry_window(minutes_of_day) -> pd.Series:
    """True where a new RTH entry is allowed (09:30 inclusive, 15:30 exclusive)."""
    return (minutes_of_day >= RTH_OPEN_MINUTES) & (minutes_of_day < RTH_ENTRY_CUTOFF_MINUTES)


def rth_session_vwap(high: pd.Series, low: pd.Series, close: pd.Series, volume: pd.Series) -> pd.Series:
    """VWAP that resets at the cash open (09:30 ET), not the CME 23:00 session."""
    minutes, dates = session_clock(close.index)
    typical = (high + low + close) / 3.0
    in_rth = minutes >= RTH_OPEN_MINUTES
    pv = (typical * volume).where(in_rth, 0.0)
    vol = volume.where(in_rth, 0.0)
    cum_pv = pv.groupby(dates).cumsum()
    cum_vol = vol.groupby(dates).cumsum()
    return cum_pv / cum_vol.replace(0, float("nan"))
