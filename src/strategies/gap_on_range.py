"""
Gap-fill vs gap-and-go classified by overnight range vs the RTH open.

Cycle-4 `gap_fill_go` used |gap vs prior RTH close| / ATR. This classifier
uses the overnight inventory range (prior 18:00 ET → 09:30 ET):

  Fill: RTH open *inside* (ONL, ONH) → fade toward overnight mid.
  Go:   RTH open *outside* ONH/ONL by `min_outside_atr` × ATR, confirmed by
        a directional first-15m close still outside the range → continue.

Stop: `stop_atr_mult` × prior-day ATR. Fill target = overnight mid; go
target = 1R. Flatten 15:45 ET. Skip short sessions. One signal per session.

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
    overnight_hl_by_date,
    prior_day_atr,
    session_clock,
    short_session_dates,
)

DRIVE_END = RTH_OPEN_MINUTES + 15
STOP_ATR_MULT = 0.35
MIN_OUTSIDE_ATR = 0.05
MIN_INSIDE_ATR = 0.05
MAX_HOLD_BARS = 72


class GapOnRangeStrategy:
    name = "gap_on_range"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        stop_atr_mult: float = STOP_ATR_MULT,
        min_outside_atr: float = MIN_OUTSIDE_ATR,
        min_inside_atr: float = MIN_INSIDE_ATR,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.stop_atr_mult = float(stop_atr_mult)
        self.min_outside_atr = float(min_outside_atr)
        self.min_inside_atr = float(min_inside_atr)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        open_ = df["open"].to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        on_hl = overnight_hl_by_date(df)
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            hl = on_hl.get(d)
            if not hl:
                continue
            onh, onl = float(hl["high"]), float(hl["low"])
            if onh <= onl:
                continue
            day_mask = date_vals == d
            open_idx = np.where(day_mask & (mins == RTH_OPEN_MINUTES))[0]
            if len(open_idx) == 0:
                open_idx = np.where(
                    day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + 5)
                )[0]
            if len(open_idx) == 0:
                continue
            i0 = int(open_idx[0])
            day_atr = float(atr_[i0])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            stop_dist = self.stop_atr_mult * day_atr
            rth_open = float(open_[i0])
            mid = 0.5 * (onh + onl)

            if onl < rth_open < onh:
                if abs(rth_open - mid) < self.min_inside_atr * day_atr:
                    continue
                fade = 1 if rth_open < mid else -1
                entries[i0] = fade
                stops[i0] = close[i0] - fade * stop_dist
                targets[i0] = mid
                continue

            outside_up = rth_open >= onh + self.min_outside_atr * day_atr
            outside_dn = rth_open <= onl - self.min_outside_atr * day_atr
            if not (outside_up or outside_dn):
                continue
            drive = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < DRIVE_END))[0]
            entry = np.where(day_mask & (mins == DRIVE_END))[0]
            if len(drive) == 0 or len(entry) == 0:
                continue
            c15 = float(close[drive[-1]])
            i = int(entry[0])
            if outside_up:
                if c15 < onh or c15 <= float(open_[drive[0]]):
                    continue
                direction = 1
            else:
                if c15 > onl or c15 >= float(open_[drive[0]]):
                    continue
                direction = -1
            entries[i] = direction
            stops[i] = close[i] - direction * stop_dist
            targets[i] = close[i] + direction * stop_dist

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
