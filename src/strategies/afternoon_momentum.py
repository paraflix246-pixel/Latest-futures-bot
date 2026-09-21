"""
Afternoon momentum: 13:30–14:30 return → 14:30 entry.

Distinct from last-30m (which uses the *first* 30m to trade 15:30).
Here the information is the post-lunch hour. Enter at 14:30 ET in that
hour's direction when |return| ≥ min_atr_frac × prior-day ATR. 1R target.
Flatten 15:30. Max hold 12 bars.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.indicators import atr
from src.strategies.session import RTH_CLOSE_MINUTES, session_clock

WINDOW_START = 13 * 60 + 30
ENTRY_MINUTES = 14 * 60 + 30
FLATTEN_MINUTES = 15 * 60 + 30
MIN_ATR_FRAC = 0.12
STOP_ATR_MULT = 0.30
MAX_HOLD_BARS = 12


class AfternoonMomentumStrategy:
    name = "afternoon_momentum"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_MINUTES
    session_exit_minutes = FLATTEN_MINUTES
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        min_atr_frac: float = MIN_ATR_FRAC,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.min_atr_frac = min_atr_frac
        self.stop_atr_mult = stop_atr_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        open_ = df["open"].to_numpy()
        close = df["close"].to_numpy()
        prior_atr = _prior_day_atr(df, dates).to_numpy()

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            day_mask = date_vals == d
            window = np.where(day_mask & (mins >= WINDOW_START) & (mins < ENTRY_MINUTES))[0]
            entry = np.where(day_mask & (mins == ENTRY_MINUTES))[0]
            if len(window) == 0 or len(entry) == 0:
                continue
            ret = float(close[window[-1]] - open_[window[0]])
            day_atr = float(prior_atr[entry[0]])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            if abs(ret) < self.min_atr_frac * day_atr:
                continue
            direction = 1 if ret > 0 else -1
            i = int(entry[0])
            stop_dist = self.stop_atr_mult * day_atr
            entries[i] = direction
            stops[i] = close[i] - direction * stop_dist
            targets[i] = close[i] + direction * stop_dist

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
