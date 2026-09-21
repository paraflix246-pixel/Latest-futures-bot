"""
Classic floor-trader pivot bounce (RTH, day-flat).

P = (prior RTH H+L+C)/3, R1=2P-L, S1=2P-H.
After 10:00, a touch of S1 then close back above S1 is long targeting P;
symmetric at R1 for shorts. Stop: 0.25 × ATR beyond the pivot. Flatten 15:45.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    prior_day_atr,
    prior_rth_hlc_by_date,
    session_clock,
    short_session_dates,
)

ENTRY_START = 10 * 60
MAX_HOLD_BARS = 36


class PivotBounceStrategy:
    name = "pivot_bounce"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(self, stop_atr_mult: float = 0.25, max_hold_bars: int = MAX_HOLD_BARS):
        self.stop_atr_mult = float(stop_atr_mult)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        prior = prior_rth_hlc_by_date(df)
        atr_ = prior_day_atr(df, dates).to_numpy()
        holidays = short_session_dates(df)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            prev = prior.get(d)
            if not prev:
                continue
            p = (prev["high"] + prev["low"] + prev["close"]) / 3.0
            r1 = 2 * p - prev["low"]
            s1 = 2 * p - prev["high"]
            watch = np.where((date_vals == d) & (mins >= ENTRY_START) & (mins < FLATTEN_1545))[0]
            touched_s = touched_r = False
            for i in watch:
                day_atr = float(atr_[i])
                if np.isnan(day_atr) or day_atr <= 0:
                    continue
                if low[i] <= s1:
                    touched_s = True
                if high[i] >= r1:
                    touched_r = True
                direction = 0
                level = p
                if touched_s and close[i] > s1:
                    direction = 1
                    level = s1
                elif touched_r and close[i] < r1:
                    direction = -1
                    level = r1
                if direction == 0:
                    continue
                stop = close[i] - direction * self.stop_atr_mult * day_atr
                risk = abs(close[i] - stop)
                if risk <= 0:
                    continue
                entries[i] = direction
                stops[i] = stop
                targets[i] = p if (direction == 1 and p > close[i]) or (direction == -1 and p < close[i]) else close[i] + direction * risk
                break
        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
