"""
Inside first-hour then range break (RTH, day-flat).

If the first 60 minutes of RTH are contained in the overnight range
(compression / "inside open"), take the first later close beyond that
first-hour high/low with VWAP alignment. Stop: first-hour opposite side.
Target 1R. Flatten 15:45. One per session.

Paper / backtest only. No live trading.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    overnight_hl_by_date,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

HOUR = 60
MAX_HOLD_BARS = 48


class InsideHourBreakStrategy:
    name = "inside_hour_break"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        hour_minutes: int = HOUR,
        require_vwap_align: bool = True,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.hour_minutes = int(hour_minutes)
        self.require_vwap_align = bool(require_vwap_align)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        on_hl = overnight_hl_by_date(df)
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            hl = on_hl.get(d)
            if not hl:
                continue
            day_mask = date_vals == d
            hour_idx = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + self.hour_minutes)
            )[0]
            watch = np.where(
                day_mask
                & (mins >= RTH_OPEN_MINUTES + self.hour_minutes)
                & (mins < FLATTEN_1545)
            )[0]
            if len(hour_idx) == 0 or len(watch) == 0:
                continue
            hh = float(high[hour_idx].max())
            ll = float(low[hour_idx].min())
            if hh <= ll:
                continue
            if hh > hl["high"] or ll < hl["low"]:
                continue
            for i in watch:
                direction = 0
                if close[i] > hh:
                    direction = 1
                elif close[i] < ll:
                    direction = -1
                if direction == 0:
                    continue
                if self.require_vwap_align:
                    if np.isnan(vwap[i]):
                        continue
                    if direction == 1 and close[i] < vwap[i]:
                        continue
                    if direction == -1 and close[i] > vwap[i]:
                        continue
                stop = ll if direction == 1 else hh
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
