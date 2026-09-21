"""
Overnight-inventory continuation into RTH (not a gap fade).

If the Globex overnight session (prior 18:00 ET → 09:30 ET) moved between
`on_atr_min` and `on_atr_max` × prior-day ATR, take the *first* RTH
pullback to session VWAP in that overnight direction after 09:45.

This is the opposite of the retired overnight-gap *reversion* hypothesis:
we fade the pullback, not the gap. Flatten 15:30. One trade per session.

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

ON_START_MINUTES = 18 * 60
ENTRY_START = RTH_OPEN_MINUTES + 15  # 09:45
ENTRY_END = 14 * 60 + 30
FLATTEN_MINUTES = 15 * 60 + 30
ON_ATR_MIN = 0.20
ON_ATR_MAX = 1.00
STOP_ATR_MULT = 0.40
MAX_HOLD_BARS = 36


class OnInventoryStrategy:
    name = "on_inventory"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = ENTRY_END
    session_exit_minutes = FLATTEN_MINUTES
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        on_atr_min: float = ON_ATR_MIN,
        on_atr_max: float = ON_ATR_MAX,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.on_atr_min = on_atr_min
        self.on_atr_max = on_atr_max
        self.stop_atr_mult = stop_atr_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        prior_atr = _prior_day_atr(df, dates).to_numpy()

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        unique_days = list(pd.unique(date_vals))

        for i, d in enumerate(unique_days):
            day_mask = date_vals == d
            # Overnight: prior day after 18:00 plus this day before 09:30.
            prev = unique_days[i - 1] if i else None
            on_idx = []
            if prev is not None:
                on_idx.extend(np.where((date_vals == prev) & (mins >= ON_START_MINUTES))[0].tolist())
            on_idx.extend(np.where(day_mask & (mins < RTH_OPEN_MINUTES))[0].tolist())
            if not on_idx:
                continue
            on_open = float(close[on_idx[0]])
            on_close = float(close[on_idx[-1]])
            on_move = on_close - on_open
            day_atr = float(prior_atr[on_idx[-1]])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            frac = abs(on_move) / day_atr
            if frac < self.on_atr_min or frac > self.on_atr_max:
                continue
            direction = 1 if on_move > 0 else -1

            watch = np.where(day_mask & (mins >= ENTRY_START) & (mins < ENTRY_END))[0]
            touched = False
            for j in watch:
                if np.isnan(vwap[j]):
                    continue
                # Pullback: price crosses/touches VWAP against the overnight direction.
                if direction == 1 and low[j] <= vwap[j] <= high[j]:
                    touched = True
                if direction == -1 and low[j] <= vwap[j] <= high[j]:
                    touched = True
                if not touched:
                    continue
                # Enter in overnight direction once VWAP is reclaimed (close back on side).
                reclaimed = (direction == 1 and close[j] >= vwap[j]) or (
                    direction == -1 and close[j] <= vwap[j]
                )
                if not reclaimed:
                    continue
                stop_dist = self.stop_atr_mult * day_atr
                if stop_dist <= 0:
                    break
                entries[j] = direction
                stops[j] = close[j] - direction * stop_dist
                targets[j] = close[j] + direction * stop_dist
                break

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
