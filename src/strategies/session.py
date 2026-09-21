"""RTH session helpers shared by the new intra-session strategies.

CME equity-index RTH is treated as 09:30–16:00 America/New_York (cash open
to cash close). Strategies in this package trade that window only and the
engine flattens at the cash close so nothing is held overnight.
"""
from __future__ import annotations

from typing import Dict, Tuple

import numpy as np
import pandas as pd

from src.strategies.indicators import atr

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


ON_START_MINUTES = 18 * 60
SHORT_SESSION_RTH_BARS = 60  # <5h of 5m RTH bars → early close / holiday
ADR_LOOKBACK = 20
FLATTEN_1545 = 15 * 60 + 45


def prior_day_atr(df: pd.DataFrame, dates: pd.Series, period: int = 14) -> pd.Series:
    daily = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    daily_atr = atr(daily["high"], daily["low"], daily["close"], period).shift(1)
    atr_by_date = {ts.date(): float(v) for ts, v in daily_atr.items()}
    series = pd.Series([atr_by_date.get(d, np.nan) for d in dates], index=df.index)
    fallback = atr(df["high"], df["low"], df["close"], period) * np.sqrt(78)
    return series.fillna(fallback)


def daily_ranges(df: pd.DataFrame) -> pd.Series:
    """Calendar-day high-low range, indexed by date."""
    daily = df.resample("1D").agg({"high": "max", "low": "min"}).dropna()
    return (daily["high"] - daily["low"]).rename("range")


def adr20_by_date(df: pd.DataFrame, lookback: int = ADR_LOOKBACK) -> Dict:
    rng = daily_ranges(df)
    adr = rng.rolling(lookback, min_periods=max(5, lookback // 2)).mean().shift(1)
    return {ts.date(): float(v) for ts, v in adr.items()}


def overnight_range_by_date(df: pd.DataFrame) -> Dict:
    """High-low from prior 18:00 ET through 09:30 ET, keyed by the RTH date."""
    minutes, dates = session_clock(df.index)
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    mins = minutes.to_numpy()
    date_vals = dates.to_numpy()
    unique = list(pd.unique(date_vals))
    out = {}
    for i, d in enumerate(unique):
        prev = unique[i - 1] if i else None
        idx = []
        if prev is not None:
            idx.extend(np.where((date_vals == prev) & (mins >= ON_START_MINUTES))[0].tolist())
        idx.extend(np.where((date_vals == d) & (mins < RTH_OPEN_MINUTES))[0].tolist())
        if not idx:
            continue
        out[d] = float(high[idx].max() - low[idx].min())
    return out


def short_session_dates(df: pd.DataFrame, min_rth_bars: int = SHORT_SESSION_RTH_BARS) -> set:
    """Dates whose RTH bar count looks like an early close or holiday."""
    minutes, dates = session_clock(df.index)
    rth = (minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_CLOSE_MINUTES)
    counts = rth.groupby(dates).sum()
    return set(counts[counts < min_rth_bars].index)


def prior_rth_hlc_by_date(df: pd.DataFrame) -> Dict:
    """Prior cash-session high/low/close keyed by the *next* RTH date."""
    minutes, dates = session_clock(df.index)
    rth = (minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_CLOSE_MINUTES)
    daily = (
        df.loc[rth]
        .assign(_d=dates[rth].to_numpy())
        .groupby("_d")
        .agg(high=("high", "max"), low=("low", "min"), close=("close", "last"))
    )
    unique = list(daily.index)
    out = {}
    for i, d in enumerate(unique):
        if i == 0:
            continue
        prev = daily.iloc[i - 1]
        out[d] = {
            "high": float(prev["high"]),
            "low": float(prev["low"]),
            "close": float(prev["close"]),
        }
    return out
