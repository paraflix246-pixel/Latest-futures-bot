"""
Fade a failed initial-balance extension.

IB = first 60 minutes (09:30–10:30 ET). If price closes beyond the IB and
then closes back inside within `failure_bars`, fade the failed break.
Stop beyond the failed extreme. Target 1.0 × IB height. Flatten 15:00.

Opposite of `ib_extension` (which trades the successful break).

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import RTH_CLOSE_MINUTES, RTH_OPEN_MINUTES, session_clock

IB_MINUTES = 60
ENTRY_END = 15 * 60
FAILURE_BARS = 4
TARGET_IB_MULT = 1.0
MAX_HOLD_BARS = 36


class FailedIbFadeStrategy:
    name = "failed_ib_fade"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = ENTRY_END
    session_exit_minutes = ENTRY_END
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        ib_minutes: int = IB_MINUTES,
        failure_bars: int = FAILURE_BARS,
        target_ib_mult: float = TARGET_IB_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.ib_minutes = ib_minutes
        self.failure_bars = failure_bars
        self.target_ib_mult = target_ib_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            day_mask = date_vals == d
            ib = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + self.ib_minutes)
            )[0]
            if len(ib) == 0:
                continue
            ib_high = float(high[ib].max())
            ib_low = float(low[ib].min())
            width = ib_high - ib_low
            if width <= 0:
                continue
            watch = np.where(
                day_mask
                & (mins >= RTH_OPEN_MINUTES + self.ib_minutes)
                & (mins < ENTRY_END)
            )[0]
            brk = 0
            extreme = 0.0
            age = 0
            for i in watch:
                if brk == 0:
                    if close[i] > ib_high:
                        brk, extreme, age = 1, float(high[i]), 0
                    elif close[i] < ib_low:
                        brk, extreme, age = -1, float(low[i]), 0
                    continue
                age += 1
                if brk == 1:
                    extreme = max(extreme, float(high[i]))
                    failed = close[i] < ib_high
                else:
                    extreme = min(extreme, float(low[i]))
                    failed = close[i] > ib_low
                if failed:
                    fade = -brk
                    entries[i] = fade
                    stops[i] = extreme
                    targets[i] = close[i] + fade * self.target_ib_mult * width
                    break
                if age >= self.failure_bars:
                    brk = 0

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
