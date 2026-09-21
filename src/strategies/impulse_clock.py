"""
Intraday impulse with a hard clock exit (RTH only).

After a large-range directional bar (range ≥ `impulse_atr_mult` × ATR and
body ≥ `min_body_range_pct` of the bar), enter in the bar's direction.
This is not an EMA/ADX trend or a Donchian channel: the only edge claim
is short-horizon continuation of a single displacement bar.

  Stop: opposite extreme of the impulse bar.
  Target: `target_r` × initial risk.
  Clock: `max_hold_bars` (default 8 × 5m = 40 minutes) then flatten.
  Session: RTH entries only; engine also flattens at 16:00 ET.
  Discipline: one signal per session, no averaging, no overnight.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.indicators import atr, sma
from src.strategies.session import (
    RTH_CLOSE_MINUTES,
    RTH_ENTRY_CUTOFF_MINUTES,
    in_rth_entry_window,
    session_clock,
)

IMPULSE_ATR_MULT = 1.8
MIN_BODY_RANGE_PCT = 0.6
VOLUME_MULT = 1.2
VOLUME_PERIOD = 20
TARGET_R = 1.5
MAX_HOLD_BARS = 8  # 40 minutes on 5m


class ImpulseClockStrategy:
    name = "impulse_clock"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = RTH_ENTRY_CUTOFF_MINUTES

    def __init__(
        self,
        impulse_atr_mult: float = IMPULSE_ATR_MULT,
        min_body_range_pct: float = MIN_BODY_RANGE_PCT,
        volume_mult: float = VOLUME_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
        target_r: float = TARGET_R,
    ):
        self.impulse_atr_mult = impulse_atr_mult
        self.min_body_range_pct = min_body_range_pct
        self.volume_mult = volume_mult
        self.max_hold_bars = max_hold_bars
        self.target_r = target_r

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        high, low, close, open_, volume = df["high"], df["low"], df["close"], df["open"], df["volume"]
        minutes, dates = session_clock(df.index)
        rth = in_rth_entry_window(minutes)

        atr_ = atr(high, low, close, 14)
        bar_range = (high - low).replace(0, np.nan)
        body = (close - open_).abs()
        impulse = bar_range >= (self.impulse_atr_mult * atr_)
        directional = (body / bar_range) >= self.min_body_range_pct
        vol_ok = volume > self.volume_mult * sma(volume, VOLUME_PERIOD)

        long_entry = impulse & directional & (close > open_) & vol_ok & rth
        short_entry = impulse & directional & (close < open_) & vol_ok & rth

        entries = pd.Series(0, index=df.index)
        stop_price = pd.Series(np.nan, index=df.index)
        target_price = pd.Series(np.nan, index=df.index)

        taken = set()
        for idx in df.index[long_entry | short_entry]:
            d = dates.loc[idx]
            if d in taken:
                continue
            if long_entry.loc[idx]:
                direction, stop = 1, float(low.loc[idx])
            else:
                direction, stop = -1, float(high.loc[idx])
            px = float(close.loc[idx])
            if (direction == 1 and px <= stop) or (direction == -1 and px >= stop):
                continue
            risk = abs(px - stop)
            if risk <= 0:
                continue
            entries.loc[idx] = direction
            stop_price.loc[idx] = stop
            target_price.loc[idx] = px + direction * self.target_r * risk
            taken.add(d)

        return StrategySignals(entries=entries, stop_price=stop_price, target_price=target_price)
