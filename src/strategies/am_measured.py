"""
First-30-minute measured move (RTH).

Take the 09:30–10:00 ET range. Direction is that window's close vs open.
At 10:00 enter with the drive; target = 10:00 close ± the 30m range (1:1
measured move); stop = opposite 30m extreme. Flatten 15:45.

Skip short sessions and inside / doji 30m windows (body < min_body_atr × ATR).
One signal per session. Paper / backtest only.
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
    session_clock,
    short_session_dates,
)

WINDOW_END = RTH_OPEN_MINUTES + 30
MIN_BODY_ATR = 0.10
MAX_HOLD_BARS = 66


class AmMeasuredMoveStrategy:
    name = "am_measured"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        min_body_atr: float = MIN_BODY_ATR,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.min_body_atr = float(min_body_atr)
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
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            win = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < WINDOW_END))[0]
            entry = np.where(day_mask & (mins == WINDOW_END))[0]
            if len(win) == 0 or len(entry) == 0:
                continue
            i = int(entry[0])
            day_atr = float(atr_[i])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            o0 = float(open_[win[0]])
            c1 = float(close[win[-1]])
            hi, lo = float(high[win].max()), float(low[win].min())
            rng = hi - lo
            body = abs(c1 - o0)
            if rng <= 0 or body < self.min_body_atr * day_atr:
                continue
            direction = 1 if c1 > o0 else -1
            entries[i] = direction
            stops[i] = lo if direction == 1 else hi
            targets[i] = c1 + direction * rng

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
