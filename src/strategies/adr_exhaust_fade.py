"""
ADR-exhaustion fade (RTH, day-flat).

After 11:00 ET, if the cash-session range already exceeds
`exhaust_mult` × 20-day ADR, fade the extreme that printed most recently:

  - high printed last → short the first close that fails to make a new high
  - low printed last → long the first close that fails to make a new low

Stop: beyond the extreme by stop_atr_mult × prior-day ATR. Target 1R.
Flatten 15:45. Skip short sessions. One signal per session.

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
    adr20_by_date,
    prior_day_atr,
    session_clock,
    short_session_dates,
)

ENTRY_START = 11 * 60
EXHAUST_MULT = 0.85
STOP_ATR_MULT = 0.25
MAX_HOLD_BARS = 48


class AdrExhaustFadeStrategy:
    name = "adr_exhaust_fade"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        exhaust_mult: float = EXHAUST_MULT,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.exhaust_mult = exhaust_mult
        self.stop_atr_mult = stop_atr_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        adr = adr20_by_date(df)
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_adr = adr.get(d)
            if not day_adr or day_adr <= 0:
                continue
            day_mask = date_vals == d
            so_far = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < ENTRY_START))[0]
            watch = np.where(day_mask & (mins >= ENTRY_START) & (mins < FLATTEN_1545))[0]
            if len(so_far) == 0 or len(watch) == 0:
                continue
            rth_high = float(high[so_far].max())
            rth_low = float(low[so_far].min())
            if (rth_high - rth_low) < self.exhaust_mult * day_adr:
                continue
            high_i = int(so_far[int(np.argmax(high[so_far]))])
            low_i = int(so_far[int(np.argmin(low[so_far]))])
            fade_high = high_i >= low_i
            for i in watch:
                rth_high = max(rth_high, float(high[i]))
                rth_low = min(rth_low, float(low[i]))
                day_atr = float(atr_[i])
                if np.isnan(day_atr) or day_atr <= 0:
                    continue
                stop_pad = self.stop_atr_mult * day_atr
                if fade_high:
                    if high[i] >= rth_high - 1e-12 and close[i] < rth_high:
                        risk = (rth_high + stop_pad) - close[i]
                        if risk <= 0:
                            continue
                        entries[i] = -1
                        stops[i] = rth_high + stop_pad
                        targets[i] = close[i] - risk
                        break
                else:
                    if low[i] <= rth_low + 1e-12 and close[i] > rth_low:
                        risk = close[i] - (rth_low - stop_pad)
                        if risk <= 0:
                            continue
                        entries[i] = 1
                        stops[i] = rth_low - stop_pad
                        targets[i] = close[i] + risk
                        break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
