"""
Morning-range break (RTH, day-flat).

Range = 09:30–11:00 ET. After 11:00, first close beyond that range with
VWAP alignment. Stop: opposite side of the morning range. Target 1R.
Flatten 15:45. One per session.

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
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

RANGE_END = 11 * 60
MAX_HOLD_BARS = 48


class MorningRangeBreakStrategy:
    name = "morning_range_break"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(self, range_end_minutes: int = RANGE_END, max_hold_bars: int = MAX_HOLD_BARS):
        self.range_end_minutes = int(range_end_minutes)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        holidays = short_session_dates(df)
        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            rng = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < self.range_end_minutes))[0]
            watch = np.where(day_mask & (mins >= self.range_end_minutes) & (mins < FLATTEN_1545))[0]
            if len(rng) == 0 or len(watch) == 0:
                continue
            rh, rl = float(high[rng].max()), float(low[rng].min())
            if rh <= rl:
                continue
            for i in watch:
                direction = 1 if close[i] > rh else (-1 if close[i] < rl else 0)
                if direction == 0:
                    continue
                if not np.isnan(vwap[i]):
                    if direction == 1 and close[i] < vwap[i]:
                        continue
                    if direction == -1 and close[i] > vwap[i]:
                        continue
                stop = rl if direction == 1 else rh
                risk = abs(close[i] - stop)
                if risk <= 0:
                    continue
                entries[i] = direction
                stops[i] = stop
                targets[i] = close[i] + direction * risk
                break
        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
