"""
Session-VWAP band fade (RTH, day-flat).

After 10:00 ET, fade the first close that sits ≥ band_atr × prior-day ATR
away from RTH VWAP, targeting VWAP. Stop is stop_atr_mult × ATR beyond
the close. Skip:

  - short / holiday sessions
  - overnight range > on_adr_mult × 20-day ADR (trend-day proxy)

One signal per session. Flatten 15:45. Paper / backtest only.

This is a mean-reversion hypothesis, not a trend-follow. Separate params
per symbol are allowed.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    adr20_by_date,
    overnight_range_by_date,
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

ENTRY_START = 10 * 60
BAND_ATR = 0.40
STOP_ATR_MULT = 0.30
ON_ADR_MULT = 1.50
MAX_HOLD_BARS = 60


class VwapBandFadeStrategy:
    name = "vwap_band_fade"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        band_atr: float = BAND_ATR,
        stop_atr_mult: float = STOP_ATR_MULT,
        on_adr_mult: float = ON_ADR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.band_atr = band_atr
        self.stop_atr_mult = stop_atr_mult
        self.on_adr_mult = on_adr_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        close = df["close"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        on_range = overnight_range_by_date(df)
        adr = adr20_by_date(df)
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            on_r = on_range.get(d)
            day_adr = adr.get(d)
            if on_r is not None and day_adr and day_adr > 0 and on_r > self.on_adr_mult * day_adr:
                continue
            day_mask = date_vals == d
            watch = np.where(day_mask & (mins >= ENTRY_START) & (mins < FLATTEN_1545))[0]
            for i in watch:
                if np.isnan(vwap[i]) or np.isnan(atr_[i]) or atr_[i] <= 0:
                    continue
                ext = close[i] - vwap[i]
                band = self.band_atr * float(atr_[i])
                if abs(ext) < band:
                    continue
                fade = -1 if ext > 0 else 1
                stop_dist = self.stop_atr_mult * float(atr_[i])
                if stop_dist <= 0:
                    break
                entries[i] = fade
                stops[i] = close[i] - fade * stop_dist
                targets[i] = vwap[i]
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
