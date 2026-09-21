"""
Lunch magnet: fade a still-extended opening range at noon.

OR = first 30 minutes of RTH. At 12:00, if close is ≥ min_away_atr × ATR
from the OR midpoint, fade toward that mid. Flatten 14:00. One signal
per session.

Clock + range location, not a multi-bar candlestick pattern.

Paper / backtest only.
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

OR_END = RTH_OPEN_MINUTES + 30
ENTRY_MINUTES = 12 * 60
FLATTEN_DEFAULT = 14 * 60
MIN_AWAY_ATR = 0.10
STOP_ATR_MULT = 0.30
MAX_HOLD_BARS = 24


class LunchOrMagnetStrategy:
    name = "lunch_or_magnet"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_DEFAULT
    session_exit_minutes = FLATTEN_DEFAULT
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        min_away_atr: float = MIN_AWAY_ATR,
        stop_atr_mult: float = STOP_ATR_MULT,
        flatten_minutes: int = FLATTEN_DEFAULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.min_away_atr = float(min_away_atr)
        self.stop_atr_mult = float(stop_atr_mult)
        self.session_exit_minutes = int(flatten_minutes)
        self.rth_entry_cutoff_minutes = int(flatten_minutes)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
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
            orb = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < OR_END))[0]
            entry = np.where(day_mask & (mins == ENTRY_MINUTES))[0]
            if len(orb) == 0 or len(entry) == 0:
                continue
            mid = 0.5 * (float(high[orb].max()) + float(low[orb].min()))
            i = int(entry[0])
            day_atr = float(atr_[i])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            away = float(close[i]) - mid
            if abs(away) < self.min_away_atr * day_atr:
                continue
            direction = -1 if away > 0 else 1
            stop_dist = self.stop_atr_mult * day_atr
            entries[i] = direction
            stops[i] = close[i] - direction * stop_dist
            targets[i] = mid

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
