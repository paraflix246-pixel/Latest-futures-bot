"""
Weekday + cash-open gap clock (minimal candlestick logic).

Trade only on `weekdays` (Mon=0). Direction is the RTH gap vs prior cash
close. Enter on the 09:30 bar; flatten at `flatten_minutes` (default 11:30).
Skip tiny gaps and short sessions.

This tests a calendar/clock effect, not a bar-pattern edge.

Paper / backtest only.
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

FLATTEN_DEFAULT = 11 * 60 + 30
MIN_GAP_ATR = 0.08
STOP_ATR_MULT = 0.30
MAX_HOLD_BARS = 30
DEFAULT_WEEKDAYS = (1, 2, 3)  # Tue–Thu


class WeekdayGapClockStrategy:
    name = "weekday_gap_clock"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_DEFAULT
    session_exit_minutes = FLATTEN_DEFAULT
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        min_gap_atr: float = MIN_GAP_ATR,
        stop_atr_mult: float = STOP_ATR_MULT,
        flatten_minutes: int = FLATTEN_DEFAULT,
        weekdays: tuple = DEFAULT_WEEKDAYS,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.min_gap_atr = float(min_gap_atr)
        self.stop_atr_mult = float(stop_atr_mult)
        self.flatten_minutes = int(flatten_minutes)
        self.session_exit_minutes = int(flatten_minutes)
        self.rth_entry_cutoff_minutes = int(flatten_minutes)
        self.weekdays = tuple(int(x) for x in weekdays)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        open_ = df["open"].to_numpy()
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
            if pd.Timestamp(d).weekday() not in self.weekdays:
                continue
            prev = prior.get(d)
            if prev is None:
                continue
            day_mask = date_vals == d
            open_idx = np.where(day_mask & (mins == RTH_OPEN_MINUTES))[0]
            if len(open_idx) == 0:
                open_idx = np.where(
                    day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + 5)
                )[0]
            if len(open_idx) == 0:
                continue
            i0 = int(open_idx[0])
            day_atr = float(atr_[i0])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            gap = float(open_[i0]) - prev["close"]
            if abs(gap) < self.min_gap_atr * day_atr:
                continue
            direction = 1 if gap > 0 else -1
            stop_dist = self.stop_atr_mult * day_atr
            entries[i0] = direction
            stops[i0] = close[i0] - direction * stop_dist
            targets[i0] = close[i0] + direction * stop_dist

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
