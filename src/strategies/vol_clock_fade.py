"""
Volume-spike then late-morning VWAP fade (volume + clock, not a candle pattern).

If the first 30 minutes of RTH print ≥ rvol_mult × the 20-session median of
that window, then after 11:00 fade the first close that is ≥ min_away_atr
from VWAP back toward VWAP. Flatten 15:45. One signal per session.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

WIN_END = RTH_OPEN_MINUTES + 30
ENTRY_START = 11 * 60
RVOL_MULT = 1.15
RVOL_LOOKBACK = 20
MIN_AWAY_ATR = 0.12
STOP_ATR_MULT = 0.30
MAX_HOLD_BARS = 54


class VolClockFadeStrategy:
    name = "vol_clock_fade"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        rvol_mult: float = RVOL_MULT,
        min_away_atr: float = MIN_AWAY_ATR,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.rvol_mult = float(rvol_mult)
        self.min_away_atr = float(min_away_atr)
        self.stop_atr_mult = float(stop_atr_mult)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        close = df["close"].to_numpy()
        volume = df["volume"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        holidays = short_session_dates(df)

        open30: dict = {}
        for d in pd.unique(date_vals):
            idx = np.where((date_vals == d) & (mins >= RTH_OPEN_MINUTES) & (mins < WIN_END))[0]
            if len(idx):
                open30[d] = float(volume[idx].sum())
        dates_sorted = list(open30)
        median_vol = {}
        for i, d in enumerate(dates_sorted):
            hist = [open30[dates_sorted[j]] for j in range(max(0, i - RVOL_LOOKBACK), i)]
            median_vol[d] = float(np.median(hist)) if len(hist) >= 8 else np.nan

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            med = median_vol.get(d, np.nan)
            vol30 = open30.get(d, 0.0)
            if np.isnan(med) or med <= 0 or vol30 < self.rvol_mult * med:
                continue
            watch = np.where((date_vals == d) & (mins >= ENTRY_START) & (mins < FLATTEN_1545))[0]
            for i in watch:
                if np.isnan(vwap[i]) or np.isnan(atr_[i]) or atr_[i] <= 0:
                    continue
                away = close[i] - vwap[i]
                if abs(away) < self.min_away_atr * float(atr_[i]):
                    continue
                fade = -1 if away > 0 else 1
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
