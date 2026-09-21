"""
Relative-volume opening 15-minute drive (RTH, day-flat).

If the first 15 minutes of cash trade print ≥ rvol_mult × the 20-session
median of that same window *and* the 15m body is directional
(≥ min_atr_frac × prior-day ATR, body/range ≥ 0.5), enter at 09:45 ET
in that direction.

Stop: stop_atr_mult × ATR. Target 1R. Flatten 12:00. Skip short sessions.
One signal per session. Paper / backtest only.
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

DRIVE_END = RTH_OPEN_MINUTES + 15
FLATTEN_MINUTES = 12 * 60
RVOL_MULT = 1.50
RVOL_LOOKBACK = 20
MIN_ATR_FRAC = 0.12
MIN_BODY_PCT = 0.50
STOP_ATR_MULT = 0.35
MAX_HOLD_BARS = 30


class RvolOpen15Strategy:
    name = "rvol_open15"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_MINUTES
    session_exit_minutes = FLATTEN_MINUTES
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        rvol_mult: float = RVOL_MULT,
        min_atr_frac: float = MIN_ATR_FRAC,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
        flatten_minutes: int = FLATTEN_MINUTES,
        min_body_pct: float = MIN_BODY_PCT,
        rvol_lookback: int = RVOL_LOOKBACK,
    ):
        self.rvol_mult = rvol_mult
        self.min_atr_frac = min_atr_frac
        self.stop_atr_mult = stop_atr_mult
        self.max_hold_bars = max_hold_bars
        self.flatten_minutes = int(flatten_minutes)
        self.session_exit_minutes = int(flatten_minutes)
        self.rth_entry_cutoff_minutes = int(flatten_minutes)
        self.min_body_pct = float(min_body_pct)
        self.rvol_lookback = int(rvol_lookback)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        open_ = df["open"].to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        volume = df["volume"].to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        holidays = short_session_dates(df)

        open15_vol: dict = {}
        for d in pd.unique(date_vals):
            idx = np.where(
                (date_vals == d) & (mins >= RTH_OPEN_MINUTES) & (mins < DRIVE_END)
            )[0]
            if len(idx):
                open15_vol[d] = float(volume[idx].sum())
        dates_sorted = list(open15_vol)
        median_vol: dict = {}
        lookback = self.rvol_lookback
        min_hist = max(3, min(8, lookback))
        for i, d in enumerate(dates_sorted):
            hist = [open15_vol[dates_sorted[j]] for j in range(max(0, i - lookback), i)]
            median_vol[d] = float(np.median(hist)) if len(hist) >= min_hist else np.nan

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            drive = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < DRIVE_END))[0]
            entry = np.where(day_mask & (mins == DRIVE_END))[0]
            if len(drive) == 0 or len(entry) == 0:
                continue
            med = median_vol.get(d, np.nan)
            vol15 = open15_vol.get(d, 0.0)
            if np.isnan(med) or med <= 0 or vol15 < self.rvol_mult * med:
                continue
            o0 = float(open_[drive[0]])
            c1 = float(close[drive[-1]])
            rng = float(high[drive].max() - low[drive].min())
            body = abs(c1 - o0)
            day_atr = float(atr_[entry[0]])
            if rng <= 0 or np.isnan(day_atr) or day_atr <= 0:
                continue
            if body < self.min_atr_frac * day_atr or (body / rng) < self.min_body_pct:
                continue
            if c1 == o0:
                continue
            direction = 1 if c1 > o0 else -1
            i = int(entry[0])
            stop_dist = self.stop_atr_mult * day_atr
            if stop_dist <= 0:
                continue
            entries[i] = direction
            stops[i] = close[i] - direction * stop_dist
            targets[i] = close[i] + direction * stop_dist

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
