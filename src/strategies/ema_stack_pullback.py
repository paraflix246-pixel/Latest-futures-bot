"""
5-minute EMA-stack pullback (RTH, day-flat).

When EMA(8) > EMA(21) > EMA(34) (or the short stack), wait for a 5m
touch of EMA(21) and a close back in the stack direction.

Stop: stop_atr_mult × prior-day ATR. Target 1R. Flatten 15:45.
Skip short sessions. One signal per session. Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.indicators import ema
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    prior_day_atr,
    session_clock,
    short_session_dates,
)

STOP_ATR_MULT = 0.35
MAX_HOLD_BARS = 36


class EmaStackPullbackStrategy:
    name = "ema_stack_pullback"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.stop_atr_mult = stop_atr_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        e8 = ema(df["close"], 8).to_numpy()
        e21 = ema(df["close"], 21).to_numpy()
        e34 = ema(df["close"], 34).to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            watch = np.where(day_mask & (mins >= RTH_OPEN_MINUTES + 30) & (mins < FLATTEN_1545))[0]
            pulled = False
            direction = 0
            for i in watch:
                if np.isnan(e8[i]) or np.isnan(e21[i]) or np.isnan(e34[i]):
                    continue
                if e8[i] > e21[i] > e34[i]:
                    direction = 1
                elif e8[i] < e21[i] < e34[i]:
                    direction = -1
                else:
                    pulled = False
                    direction = 0
                    continue
                if low[i] <= e21[i] <= high[i]:
                    pulled = True
                if not pulled:
                    continue
                resume = (direction == 1 and close[i] > e21[i]) or (
                    direction == -1 and close[i] < e21[i]
                )
                if not resume or np.isnan(atr_[i]) or atr_[i] <= 0:
                    continue
                stop_dist = self.stop_atr_mult * float(atr_[i])
                entries[i] = direction
                stops[i] = close[i] - direction * stop_dist
                targets[i] = close[i] + direction * stop_dist
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
