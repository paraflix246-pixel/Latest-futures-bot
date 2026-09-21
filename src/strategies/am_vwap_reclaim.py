"""
Morning VWAP reclaim in the first-hour direction.

Bias = sign of 09:30–10:30 close vs open. After 10:30, the first touch of
RTH VWAP that then closes back on the bias side is the entry. Stop
`stop_atr_mult` × prior-day ATR. Flatten 14:00. One trade per session.

Not a VWAP-cross EMA system and not overnight inventory.

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

HOUR_END = RTH_OPEN_MINUTES + 60
ENTRY_END = 14 * 60
STOP_ATR_MULT = 0.35
MAX_HOLD_BARS = 36


class AmVwapReclaimStrategy:
    name = "am_vwap_reclaim"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = ENTRY_END
    session_exit_minutes = ENTRY_END
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.stop_atr_mult = stop_atr_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        open_ = df["open"].to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        prior_atr = _prior_day_atr(df, dates).to_numpy()

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            day_mask = date_vals == d
            first = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < HOUR_END))[0]
            if len(first) == 0:
                continue
            bias = 1 if close[first[-1]] > open_[first[0]] else -1
            watch = np.where(day_mask & (mins >= HOUR_END) & (mins < ENTRY_END))[0]
            touched = False
            for i in watch:
                if np.isnan(vwap[i]):
                    continue
                if low[i] <= vwap[i] <= high[i]:
                    touched = True
                if not touched:
                    continue
                reclaimed = (bias == 1 and close[i] >= vwap[i]) or (bias == -1 and close[i] <= vwap[i])
                if not reclaimed:
                    continue
                day_atr = float(prior_atr[i])
                if np.isnan(day_atr) or day_atr <= 0:
                    break
                stop_dist = self.stop_atr_mult * day_atr
                entries[i] = bias
                stops[i] = close[i] - bias * stop_dist
                targets[i] = close[i] + bias * stop_dist
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
