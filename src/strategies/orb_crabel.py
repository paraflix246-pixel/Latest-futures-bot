"""
Filtered RTH opening-range breakout (Crabel-style) + failure fade.

Hypothesis, not a claimed edge. Close-beyond-OR only (not a tick pierce),
with three filters taken from published ORB playbooks:

  1. RTH VWAP alignment (long only above VWAP, short only below).
  2. Breakout-bar RVOL ≥ `rvol_mult` × average volume inside the OR.
  3. OR width vs prior-day ATR(14): skip if width is outside
     [`or_atr_min`, `or_atr_max`] (default 15–50% of ATR).

Failure fade: if a break attempt closes back inside the OR within
`failure_bars`, fade with a stop beyond the failed extreme.

Clock: no new entries after 11:00 ET; engine time-stops at 11:00 and
still flattens any residual at 16:00. One break and one fade signal per
session. No averaging, no overnight.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.indicators import atr
from src.strategies.session import (
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    rth_session_vwap,
    session_clock,
)

OR_MINUTES = 15
RVOL_MULT = 1.5
OR_ATR_MIN = 0.15
OR_ATR_MAX = 0.50
FAILURE_BARS = 4
TARGET_OR_MULT = 1.5
CLOCK_EXIT_MINUTES = 11 * 60  # 11:00 ET


class OrbCrabelStrategy:
    name = "orb_crabel"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = CLOCK_EXIT_MINUTES
    session_exit_minutes = CLOCK_EXIT_MINUTES
    max_hold_bars = 24  # safety cap; 11:00 clock is the real time stop

    def __init__(
        self,
        or_minutes: int = OR_MINUTES,
        rvol_mult: float = RVOL_MULT,
        or_atr_min: float = OR_ATR_MIN,
        or_atr_max: float = OR_ATR_MAX,
        failure_bars: int = FAILURE_BARS,
        target_or_mult: float = TARGET_OR_MULT,
    ):
        self.or_minutes = or_minutes
        self.rvol_mult = rvol_mult
        self.or_atr_min = or_atr_min
        self.or_atr_max = or_atr_max
        self.failure_bars = failure_bars
        self.target_or_mult = target_or_mult

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        volume = df["volume"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        prior_atr = _prior_day_atr(df, dates).to_numpy()

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
            or_width = or_high - or_low
            if or_width <= 0:
                continue
            day_atr = float(prior_atr[or_idx[-1]])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            width_frac = or_width / day_atr
            if width_frac < self.or_atr_min or width_frac > self.or_atr_max:
                continue

            or_avg_vol = float(volume[or_idx].mean())
            watch_idx = np.where(
                day_mask
                & (mins >= RTH_OPEN_MINUTES + self.or_minutes)
                & (mins < CLOCK_EXIT_MINUTES)
            )[0]

            breakout_dir = 0
            breakout_extreme = 0.0
            bars_since_break = 0
            issued_break = False
            issued_fade = False

            for i in watch_idx:
                if breakout_dir == 0:
                    if close[i] > or_high:
                        breakout_dir, breakout_extreme, bars_since_break = 1, float(high[i]), 0
                        if (
                            (not issued_break)
                            and volume[i] >= self.rvol_mult * or_avg_vol
                            and close[i] > vwap[i]
                        ):
                            issued_break = _emit_or(
                                entries, stops, targets, close, i, 1, or_low, or_width, self.target_or_mult
                            )
                    elif close[i] < or_low:
                        breakout_dir, breakout_extreme, bars_since_break = -1, float(low[i]), 0
                        if (
                            (not issued_break)
                            and volume[i] >= self.rvol_mult * or_avg_vol
                            and close[i] < vwap[i]
                        ):
                            issued_break = _emit_or(
                                entries, stops, targets, close, i, -1, or_high, or_width, self.target_or_mult
                            )
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
                    issued_fade = _emit_or(
                        entries, stops, targets, close, i, fade_dir, breakout_extreme, or_width, self.target_or_mult
                    )
                    breakout_dir = 0
                elif bars_since_break >= self.failure_bars:
                    breakout_dir = 0

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )


def _prior_day_atr(df: pd.DataFrame, dates: pd.Series) -> pd.Series:
    daily = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    daily_atr = atr(daily["high"], daily["low"], daily["close"], 14).shift(1)
    atr_by_date = {ts.date(): float(v) for ts, v in daily_atr.items()}
    series = pd.Series([atr_by_date.get(d, np.nan) for d in dates], index=df.index)
    fallback = atr(df["high"], df["low"], df["close"], 14) * np.sqrt(78)
    return series.fillna(fallback)


def _emit_or(entries, stops, targets, close, i, direction, stop, or_width, target_or_mult) -> bool:
    if direction == 1 and close[i] <= stop:
        return False
    if direction == -1 and close[i] >= stop:
        return False
    entries[i] = direction
    stops[i] = stop
    targets[i] = close[i] + direction * target_or_mult * or_width
    return True
