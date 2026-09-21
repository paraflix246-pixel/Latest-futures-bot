"""
Overnight gap-and-go (RTH, day-flat).

If the cash-open gap vs prior RTH close is ≥ min_gap_atr × ATR *and*
the first 15 minutes continue that direction, enter at 09:45 with the
drive. Opposite of a gap *fill*. Flatten 11:30. Target 1R.

Paper / backtest only. No live trading.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import (
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    prior_day_atr,
    prior_rth_hlc_by_date,
    session_clock,
    short_session_dates,
)

DRIVE_END = RTH_OPEN_MINUTES + 15
FLATTEN = 11 * 60 + 30
MIN_GAP_ATR = 0.25
MIN_BODY = 0.12
STOP_ATR = 0.30
MAX_HOLD_BARS = 24


class GapAndGoStrategy:
    name = "gap_and_go"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN
    session_exit_minutes = FLATTEN
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        min_gap_atr: float = MIN_GAP_ATR,
        stop_atr_mult: float = STOP_ATR,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.min_gap_atr = float(min_gap_atr)
        self.stop_atr_mult = float(stop_atr_mult)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        open_ = df["open"].to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        prior = prior_rth_hlc_by_date(df)
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            prev = prior.get(d)
            if prev is None:
                continue
            day_mask = date_vals == d
            open_idx = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + 5))[0]
            drive = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < DRIVE_END))[0]
            entry = np.where(day_mask & (mins == DRIVE_END))[0]
            if len(open_idx) == 0 or len(drive) == 0 or len(entry) == 0:
                continue
            i0 = int(open_idx[0])
            day_atr = float(atr_[i0])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            gap = float(open_[i0]) - prev["close"]
            if abs(gap) < self.min_gap_atr * day_atr:
                continue
            o0 = float(open_[drive[0]])
            c1 = float(close[drive[-1]])
            body = c1 - o0
            if gap > 0 and body < MIN_BODY * day_atr:
                continue
            if gap < 0 and body > -MIN_BODY * day_atr:
                continue
            direction = 1 if gap > 0 else -1
            i = int(entry[0])
            stop_dist = self.stop_atr_mult * day_atr
            if stop_dist <= 0:
                continue
            entries[i] = direction
            stops[i] = close[i] - direction * stop_dist
            targets[i] = close[i] + direction * stop_dist

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
