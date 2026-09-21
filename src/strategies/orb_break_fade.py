"""
Opening-range breakout + failure-fade (RTH only).

One session-level state machine, not a retune of the existing standalone
`orb` / `orb_failure` modules:

  1. Opening range = high/low of the first `or_minutes` after 09:30 ET.
  2. Breakout: first close beyond the range with volume confirmation enters
     WITH the break. Stop sits at the broken level so a failed break is
     stopped out instead of being held across the range (no clinging).
  3. Failure-fade: if a break attempt (close beyond the range) then closes
     back inside within `failure_bars`, fade with a tight stop beyond the
     failed extreme. This can fire after a stopped-out breakout or instead
     of a breakout that lacked volume.
  4. Fixed `target_r` * initial risk. Engine hard-flattens at 16:00 ET and
     applies `max_hold_bars`. No averaging; at most one break and one fade
     signal per session.

Paper / backtest only. No overnight holds.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.indicators import atr
from src.strategies.session import (
    RTH_CLOSE_MINUTES,
    RTH_ENTRY_CUTOFF_MINUTES,
    RTH_OPEN_MINUTES,
    session_clock,
)

OR_MINUTES = 15
ENTRY_WINDOW_MINUTES = 150
VOLUME_MULT = 1.3
FAILURE_BARS = 4
TARGET_R = 1.5
MAX_HOLD_BARS = 36  # 3 hours on 5m
ATR_STOP_PAD = 0.15  # fraction of ATR beyond the structural stop


class OrbBreakFadeStrategy:
    name = "orb_break_fade"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = RTH_ENTRY_CUTOFF_MINUTES

    def __init__(
        self,
        or_minutes: int = OR_MINUTES,
        entry_window_minutes: int = ENTRY_WINDOW_MINUTES,
        volume_mult: float = VOLUME_MULT,
        failure_bars: int = FAILURE_BARS,
        target_r: float = TARGET_R,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.or_minutes = or_minutes
        self.entry_window_minutes = entry_window_minutes
        self.volume_mult = volume_mult
        self.failure_bars = failure_bars
        self.target_r = target_r
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        volume = df["volume"].to_numpy()
        atr_ = atr(df["high"], df["low"], df["close"], 14).to_numpy()

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            day_mask = date_vals == d
            or_idx = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + self.or_minutes)
            )[0]
            if len(or_idx) == 0:
                continue

            or_high = float(high[or_idx].max())
            or_low = float(low[or_idx].min())
            if or_high <= or_low:
                continue
            or_avg_vol = float(volume[or_idx].mean())

            watch_end = RTH_OPEN_MINUTES + self.or_minutes + self.entry_window_minutes
            watch_idx = np.where(
                day_mask
                & (mins >= RTH_OPEN_MINUTES + self.or_minutes)
                & (mins < min(watch_end, RTH_ENTRY_CUTOFF_MINUTES))
            )[0]

            breakout_dir = 0
            breakout_extreme = 0.0
            bars_since_break = 0
            issued_break = False
            issued_fade = False

            for i in watch_idx:
                pad = float(atr_[i]) * ATR_STOP_PAD if not np.isnan(atr_[i]) else (or_high - or_low) * 0.05

                if breakout_dir == 0:
                    if close[i] > or_high:
                        breakout_dir, breakout_extreme, bars_since_break = 1, float(high[i]), 0
                        if (not issued_break) and volume[i] > self.volume_mult * or_avg_vol:
                            stop = or_high - pad
                            issued_break = _emit(entries, stops, targets, close, i, 1, stop, self.target_r)
                    elif close[i] < or_low:
                        breakout_dir, breakout_extreme, bars_since_break = -1, float(low[i]), 0
                        if (not issued_break) and volume[i] > self.volume_mult * or_avg_vol:
                            stop = or_low + pad
                            issued_break = _emit(entries, stops, targets, close, i, -1, stop, self.target_r)
                    continue

                bars_since_break += 1
                if breakout_dir == 1:
                    breakout_extreme = max(breakout_extreme, float(high[i]))
                    failed = close[i] < or_high
                else:
                    breakout_extreme = min(breakout_extreme, float(low[i]))
                    failed = close[i] > or_low

                if failed and not issued_fade:
                    fade_dir = -breakout_dir
                    stop = breakout_extreme + pad if fade_dir == -1 else breakout_extreme - pad
                    issued_fade = _emit(entries, stops, targets, close, i, fade_dir, stop, self.target_r)
                    breakout_dir = 0
                elif bars_since_break >= self.failure_bars:
                    # Held outside the range — do not fade a working break.
                    breakout_dir = 0

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )


def _emit(entries, stops, targets, close, i, direction, stop, target_r) -> bool:
    risk = abs(close[i] - stop)
    if risk <= 0:
        return False
    if direction == 1 and close[i] <= stop:
        return False
    if direction == -1 and close[i] >= stop:
        return False
    entries[i] = direction
    stops[i] = stop
    targets[i] = close[i] + direction * target_r * risk
    return True
