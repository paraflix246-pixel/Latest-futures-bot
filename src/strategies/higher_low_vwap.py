"""
Morning higher-low / lower-high VWAP continuation (RTH, day-flat).

The first 30 minutes set a reference low/high. After 10:00, if price
makes a higher low vs that reference (long) or a lower high (short)
and then closes back through RTH VWAP in that direction, enter.
Stop: stop_atr_mult × ATR. Target 1R. Flatten 15:45. One per session.

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
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

REF_END = RTH_OPEN_MINUTES + 30
ENTRY_START = 10 * 60
STOP_ATR = 0.30
MAX_HOLD_BARS = 48


class HigherLowVwapStrategy:
    name = "higher_low_vwap"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        stop_atr_mult: float = STOP_ATR,
        entry_start_minutes: int = ENTRY_START,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.stop_atr_mult = float(stop_atr_mult)
        self.entry_start_minutes = int(entry_start_minutes)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            ref = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < REF_END))[0]
            watch = np.where(
                day_mask & (mins >= self.entry_start_minutes) & (mins < FLATTEN_1545)
            )[0]
            if len(ref) == 0 or len(watch) == 0:
                continue
            ref_low = float(low[ref].min())
            ref_high = float(high[ref].max())
            crossed_below = False
            crossed_above = False
            post_low = float("inf")
            post_high = float("-inf")
            for i in watch:
                post_low = min(post_low, float(low[i]))
                post_high = max(post_high, float(high[i]))
                if np.isnan(vwap[i]):
                    continue
                if close[i] < vwap[i]:
                    crossed_below = True
                if close[i] > vwap[i]:
                    crossed_above = True
                day_atr = float(atr_[i])
                if np.isnan(day_atr) or day_atr <= 0:
                    continue
                direction = 0
                if post_low > ref_low and crossed_below and close[i] > vwap[i]:
                    direction = 1
                elif post_high < ref_high and crossed_above and close[i] < vwap[i]:
                    direction = -1
                if direction == 0:
                    continue
                stop_dist = self.stop_atr_mult * day_atr
                if stop_dist <= 0:
                    break
                entries[i] = direction
                stops[i] = close[i] - direction * stop_dist
                targets[i] = close[i] + direction * stop_dist
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
