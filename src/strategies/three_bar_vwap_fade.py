"""
Three-bar exhaustion fade into VWAP (RTH, day-flat).

After 10:00, if three consecutive 5m closes print further from RTH VWAP
in the same direction, fade the third close back toward VWAP.

Stop: stop_atr_mult × prior-day ATR. Target = VWAP. Flatten 15:45.
Skip short sessions. One signal per session. Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

ENTRY_START = 10 * 60
STOP_ATR_MULT = 0.30
MAX_HOLD_BARS = 36


class ThreeBarVwapFadeStrategy:
    name = "three_bar_vwap_fade"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
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
        close = df["close"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            watch = np.where(day_mask & (mins >= ENTRY_START) & (mins < FLATTEN_1545))[0]
            dist_hist = []
            for i in watch:
                if np.isnan(vwap[i]):
                    dist_hist = []
                    continue
                dist = close[i] - vwap[i]
                dist_hist.append(dist)
                if len(dist_hist) < 3:
                    continue
                a, b, c = dist_hist[-3:]
                away = (c > b > a > 0) or (c < b < a < 0)
                if not away or np.isnan(atr_[i]) or atr_[i] <= 0:
                    continue
                fade = -1 if c > 0 else 1
                stop_dist = self.stop_atr_mult * float(atr_[i])
                entries[i] = fade
                stops[i] = close[i] - fade * stop_dist
                targets[i] = vwap[i]
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
