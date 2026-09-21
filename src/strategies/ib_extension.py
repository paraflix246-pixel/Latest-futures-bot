"""
Initial-balance extension (Market Profile first hour), RTH only.

Distinct from 15/30-minute ORB: the range is the first *60 minutes*
(09:30–10:30 ET). After 10:30, the first close beyond the IB with volume
confirmation enters in the break direction. Stop is the IB midpoint so a
failed extension does not cling across the whole morning range.

  Target: 1.0 × IB height.
  Clock: no new entries after 14:30 ET; flatten 15:45 / 16:00.
  One trade per session. No overnight.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import RTH_CLOSE_MINUTES, RTH_OPEN_MINUTES, session_clock

IB_MINUTES = 60
ENTRY_END_MINUTES = 14 * 60 + 30
FLATTEN_MINUTES = 15 * 60 + 45
VOLUME_MULT = 1.2
TARGET_IB_MULT = 1.0
MAX_HOLD_BARS = 48


class IbExtensionStrategy:
    name = "ib_extension"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = ENTRY_END_MINUTES
    session_exit_minutes = FLATTEN_MINUTES
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        ib_minutes: int = IB_MINUTES,
        volume_mult: float = VOLUME_MULT,
        target_ib_mult: float = TARGET_IB_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.ib_minutes = ib_minutes
        self.volume_mult = volume_mult
        self.target_ib_mult = target_ib_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        volume = df["volume"].to_numpy()

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            day_mask = date_vals == d
            ib_idx = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + self.ib_minutes)
            )[0]
            if len(ib_idx) == 0:
                continue
            ib_high = float(high[ib_idx].max())
            ib_low = float(low[ib_idx].min())
            ib_width = ib_high - ib_low
            if ib_width <= 0:
                continue
            ib_mid = (ib_high + ib_low) / 2.0
            ib_vol = float(volume[ib_idx].mean())
            watch = np.where(
                day_mask
                & (mins >= RTH_OPEN_MINUTES + self.ib_minutes)
                & (mins < ENTRY_END_MINUTES)
            )[0]
            for i in watch:
                vol_ok = volume[i] > self.volume_mult * ib_vol
                if close[i] > ib_high and vol_ok:
                    entries[i] = 1
                    stops[i] = ib_mid
                    targets[i] = close[i] + self.target_ib_mult * ib_width
                    break
                if close[i] < ib_low and vol_ok:
                    entries[i] = -1
                    stops[i] = ib_mid
                    targets[i] = close[i] - self.target_ib_mult * ib_width
                    break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
