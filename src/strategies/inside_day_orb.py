"""
Inside-day opening-range break (RTH, day-flat).

If the prior RTH session was inside the session before it, take today's
15-minute OR break, VWAP-aligned. Stop: OR mid. Target 1R. Flatten 15:45.

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
    prior_rth_hlc_by_date,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

OR_MINUTES = 15
MAX_HOLD_BARS = 48


class InsideDayOrbStrategy:
    name = "inside_day_orb"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(self, or_minutes: int = OR_MINUTES, max_hold_bars: int = MAX_HOLD_BARS):
        self.or_minutes = int(or_minutes)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        prior = prior_rth_hlc_by_date(df)
        # Map date -> prior-prior via chaining prior[d] is previous RTH,
        # so inside if prior high/low contained in the session before that.
        unique = list(pd.unique(dates.to_numpy()))
        prev_map = {}
        for i, d in enumerate(unique):
            if i < 2:
                continue
            p1 = prior.get(d)
            p2 = prior.get(unique[i - 1])
            if p1 and p2:
                prev_map[d] = p1["high"] <= p2["high"] and p1["low"] >= p2["low"]

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

        for d in unique:
            if d in holidays or not prev_map.get(d):
                continue
            day_mask = date_vals == d
            or_idx = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + self.or_minutes)
            )[0]
            watch = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES + self.or_minutes) & (mins < FLATTEN_1545)
            )[0]
            if len(or_idx) == 0 or len(watch) == 0:
                continue
            oh, ol = float(high[or_idx].max()), float(low[or_idx].min())
            mid = 0.5 * (oh + ol)
            if oh <= ol:
                continue
            for i in watch:
                direction = 1 if close[i] > oh else (-1 if close[i] < ol else 0)
                if direction == 0:
                    continue
                if not np.isnan(vwap[i]):
                    if direction == 1 and close[i] < vwap[i]:
                        continue
                    if direction == -1 and close[i] > vwap[i]:
                        continue
                risk = abs(close[i] - mid)
                if risk <= 0:
                    continue
                entries[i] = direction
                stops[i] = mid
                targets[i] = close[i] + direction * risk
                break
        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
