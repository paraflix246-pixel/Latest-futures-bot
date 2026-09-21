"""
Last-30-minute session-return continuation (day-only).

Academic intra-day momentum papers (first-half / first-30m return predicting
the last ~30m) are treated here as a hypothesis, not a published edge —
costs often wipe the effect. Conservative day-only version:

  1. Measure the first-30-minute RTH return (09:30–10:00 ET close vs open).
  2. Require |first30| ≥ `min_ret_atr_frac` × (prior-day ATR / open).
  3. At 15:30 ET (start of the last 30m) enter in the first-30m direction.
  4. Stop: `stop_atr_mult` × prior-day ATR. Target: 1R.
  5. Flatten at 16:00 ET. Max hold 6 bars. One trade per session.
     No overnight, no averaging.

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
    session_clock,
)

FIRST30_END = RTH_OPEN_MINUTES + 30  # 10:00 ET
ENTRY_MINUTES = 15 * 60 + 30         # 15:30 ET
# Engine cutoff is >= this minute; must sit *after* the 15:30 entry bar.
ENTRY_CUTOFF_MINUTES = 15 * 60 + 35
MIN_RET_ATR_FRAC = 0.15
STOP_ATR_MULT = 0.35
MAX_HOLD_BARS = 6


class Last30MomentumStrategy:
    name = "last30_momentum"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = ENTRY_CUTOFF_MINUTES
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        min_ret_atr_frac: float = MIN_RET_ATR_FRAC,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.min_ret_atr_frac = min_ret_atr_frac
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
            first_idx = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < FIRST30_END))[0]
            entry_idx = np.where(day_mask & (mins == ENTRY_MINUTES))[0]
            if len(first_idx) == 0 or len(entry_idx) == 0:
                continue

            session_open = float(open_[first_idx[0]])
            first30_close = float(close[first_idx[-1]])
            if session_open <= 0:
                continue
            first30_ret = (first30_close - session_open) / session_open
            day_atr = float(prior_atr[entry_idx[0]])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            thresh = self.min_ret_atr_frac * (day_atr / session_open)
            if abs(first30_ret) < thresh:
                continue

            i = int(entry_idx[0])
            direction = 1 if first30_ret > 0 else -1
            stop_dist = self.stop_atr_mult * day_atr
            stop = close[i] - direction * stop_dist
            target = close[i] + direction * stop_dist
            if stop_dist <= 0:
                continue
            entries[i] = direction
            stops[i] = stop
            targets[i] = target

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
