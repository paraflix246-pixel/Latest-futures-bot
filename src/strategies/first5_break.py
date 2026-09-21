"""
First-five-minute opening-range break (1m path inside a 5m bar).

OR = 09:30–09:35 ET. After that window, the first close beyond OR high/low
enters in the break direction. Stop ATR, target 1R, flatten 11:00.
Skip tiny ranges and short sessions.

On 5m this collapses to a 1-bar OR (the first cash bar). The hypothesis is
the 1m path, not the 5m candlestick.

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
    session_clock,
    short_session_dates,
)

OR_MINUTES = 5
ENTRY_END = 11 * 60
MIN_OR_ATR = 0.04
STOP_ATR_MULT = 0.30
MAX_HOLD_BARS = 90


class First5BreakStrategy:
    name = "first5_break"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = ENTRY_END
    session_exit_minutes = ENTRY_END
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        or_minutes: int = OR_MINUTES,
        min_or_atr: float = MIN_OR_ATR,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.or_minutes = int(or_minutes)
        self.min_or_atr = float(min_or_atr)
        self.stop_atr_mult = float(stop_atr_mult)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)
        or_end = RTH_OPEN_MINUTES + self.or_minutes

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            orb = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < or_end))[0]
            watch = np.where(day_mask & (mins >= or_end) & (mins < ENTRY_END))[0]
            if len(orb) == 0 or len(watch) == 0:
                continue
            orh, orl = float(high[orb].max()), float(low[orb].min())
            width = orh - orl
            i_atr = int(watch[0])
            day_atr = float(atr_[i_atr])
            if np.isnan(day_atr) or day_atr <= 0 or width < self.min_or_atr * day_atr:
                continue
            stop_dist = self.stop_atr_mult * day_atr
            for i in watch:
                if close[i] > orh:
                    direction = 1
                elif close[i] < orl:
                    direction = -1
                else:
                    continue
                entries[i] = direction
                stops[i] = close[i] - direction * stop_dist
                targets[i] = close[i] + direction * stop_dist
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
