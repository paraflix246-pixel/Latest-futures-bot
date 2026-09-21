"""
VWAP-aligned pullback continuation (RTH, day-flat).

Trend-day hypothesis, the opposite of `vwap_band_fade`:

  1. After 10:00, require 6 consecutive 5m closes on one side of RTH VWAP.
  2. Wait for a pullback that touches VWAP.
  3. Enter when the close resumes on the trend side of VWAP.

Skip overnight-expansion days (>1.5× ADR). Stop: stop_atr_mult × ATR
beyond VWAP. Target 1R. Flatten 15:45. One signal per session.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    adr20_by_date,
    overnight_range_by_date,
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

ENTRY_START = 10 * 60
ALIGN_BARS = 6
STOP_ATR_MULT = 0.30
ON_ADR_MULT = 1.50
MAX_HOLD_BARS = 48


class VwapPullbackContStrategy:
    name = "vwap_pullback_cont"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        align_bars: int = ALIGN_BARS,
        stop_atr_mult: float = STOP_ATR_MULT,
        on_adr_mult: float = ON_ADR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.align_bars = align_bars
        self.stop_atr_mult = stop_atr_mult
        self.on_adr_mult = on_adr_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
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
            streak = 0
            bias = 0
            pulled = False
            for i in watch:
                if np.isnan(vwap[i]):
                    continue
                side = 1 if close[i] > vwap[i] else (-1 if close[i] < vwap[i] else 0)
                if bias == 0:
                    if side == 0:
                        streak = 0
                        continue
                    if side == (1 if streak >= 0 else -1) or streak == 0:
                        streak = streak + side if (streak == 0 or np.sign(streak) == side) else side
                    else:
                        streak = side
                    if abs(streak) >= self.align_bars:
                        bias = int(np.sign(streak))
                    continue
                if low[i] <= vwap[i] <= high[i]:
                    pulled = True
                if not pulled:
                    continue
                resume = (bias == 1 and close[i] > vwap[i]) or (bias == -1 and close[i] < vwap[i])
                if not resume or np.isnan(atr_[i]) or atr_[i] <= 0:
                    continue
                stop_dist = self.stop_atr_mult * float(atr_[i])
                entries[i] = bias
                stops[i] = vwap[i] - bias * stop_dist
                targets[i] = close[i] + bias * abs(close[i] - (vwap[i] - bias * stop_dist))
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
