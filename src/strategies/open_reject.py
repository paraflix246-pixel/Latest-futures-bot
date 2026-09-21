"""
Opening-range rejection: fade an extreme first-15m close back to VWAP.

If the first 15 minutes of RTH close in the outer `extreme_frac` of that
window's range *and* on the far side of RTH VWAP, fade toward VWAP at 09:45.
Stop beyond the 15m extreme. Target VWAP (clamped to 1R if farther).
Flatten 15:45. Skip short sessions. One signal per session.

Not an ORB and not the cycle-4 morning_reversal (which used IB mid).

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

DRIVE_END = RTH_OPEN_MINUTES + 15
EXTREME_FRAC = 0.25
STOP_ATR_MULT = 0.30
MAX_HOLD_BARS = 72


class OpenRejectStrategy:
    name = "open_reject"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        extreme_frac: float = EXTREME_FRAC,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.extreme_frac = float(extreme_frac)
        self.stop_atr_mult = float(stop_atr_mult)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            drive = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < DRIVE_END))[0]
            entry = np.where(day_mask & (mins == DRIVE_END))[0]
            if len(drive) == 0 or len(entry) == 0:
                continue
            hi, lo = float(high[drive].max()), float(low[drive].min())
            rng = hi - lo
            if rng <= 0:
                continue
            c15 = float(close[drive[-1]])
            loc = (c15 - lo) / rng
            i = int(entry[0])
            if np.isnan(vwap[i]):
                continue
            day_atr = float(atr_[i])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            stop_dist = self.stop_atr_mult * day_atr
            if loc >= 1.0 - self.extreme_frac and c15 > vwap[i]:
                fade = -1
            elif loc <= self.extreme_frac and c15 < vwap[i]:
                fade = 1
            else:
                continue
            entries[i] = fade
            if fade == -1:
                stops[i] = hi + max(stop_dist * 0.25, 1e-6)
            else:
                stops[i] = lo - max(stop_dist * 0.25, 1e-6)
            tpx = float(vwap[i])
            risk = abs(close[i] - stops[i])
            if risk <= 0:
                continue
            if abs(tpx - close[i]) > risk:
                tpx = close[i] + fade * risk
            targets[i] = tpx

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
