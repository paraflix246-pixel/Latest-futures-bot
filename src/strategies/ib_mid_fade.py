"""
Initial-balance midpoint fade (RTH, day-flat).

After 10:30 ET, if price extends ≥ ext_atr × prior-day ATR beyond the
first-hour midpoint, fade back toward that midpoint.

Stop: stop_atr_mult × ATR beyond the close. Target = IB mid.
Flatten 15:00. Skip short sessions. One signal per session.

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

IB_END = RTH_OPEN_MINUTES + 60
FLATTEN_MINUTES = 15 * 60
EXT_ATR = 0.35
STOP_ATR_MULT = 0.30
MAX_HOLD_BARS = 48


class IbMidFadeStrategy:
    name = "ib_mid_fade"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_MINUTES
    session_exit_minutes = FLATTEN_MINUTES
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        ext_atr: float = EXT_ATR,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.ext_atr = ext_atr
        self.stop_atr_mult = stop_atr_mult
        self.max_hold_bars = max_hold_bars

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
            ib = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < IB_END))[0]
            if len(ib) == 0:
                continue
            mid = 0.5 * (float(high[ib].max()) + float(low[ib].min()))
            watch = np.where(day_mask & (mins >= IB_END) & (mins < FLATTEN_MINUTES))[0]
            for i in watch:
                day_atr = float(atr_[i])
                if np.isnan(day_atr) or day_atr <= 0:
                    continue
                ext = close[i] - mid
                if abs(ext) < self.ext_atr * day_atr:
                    continue
                fade = -1 if ext > 0 else 1
                stop_dist = self.stop_atr_mult * day_atr
                entries[i] = fade
                stops[i] = close[i] - fade * stop_dist
                targets[i] = mid
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
