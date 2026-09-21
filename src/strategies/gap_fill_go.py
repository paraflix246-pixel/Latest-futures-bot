"""
Gap-fill versus gap-and-go (RTH, day-flat).

Classify the cash-open gap vs the prior RTH close:

  Fill: |gap| ≥ min_gap_atr × prior-day ATR → fade toward yesterday's
        RTH close. Enter on the first 09:35–10:30 bar that has not
        already filled the gap. Target = prior close. Flatten 11:00.
  Go:   smaller gap plus a directional first 15 minutes (body ≥
        min_drive_atr × ATR and body/range ≥ 0.5) → enter at 09:45
        with the drive. Flatten 11:30.

Skip short sessions. One signal per session. Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import (
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    prior_day_atr,
    prior_rth_hlc_by_date,
    session_clock,
    short_session_dates,
)

MIN_GAP_ATR = 0.40
MIN_DRIVE_ATR = 0.12
MIN_BODY_PCT = 0.50
STOP_ATR_MULT = 0.35
FILL_FLAT = 11 * 60
GO_FLAT = 11 * 60 + 30
DRIVE_END = RTH_OPEN_MINUTES + 15
MAX_HOLD_BARS = 24


class GapFillGoStrategy:
    name = "gap_fill_go"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = GO_FLAT
    session_exit_minutes = GO_FLAT
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        min_gap_atr: float = MIN_GAP_ATR,
        min_drive_atr: float = MIN_DRIVE_ATR,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.min_gap_atr = min_gap_atr
        self.min_drive_atr = min_drive_atr
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
        atr_ = prior_day_atr(df, dates).to_numpy()
        prior = prior_rth_hlc_by_date(df)
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            prev = prior.get(d)
            if prev is None:
                continue
            day_mask = date_vals == d
            open_idx = np.where(day_mask & (mins == RTH_OPEN_MINUTES))[0]
            if len(open_idx) == 0:
                open_idx = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + 5))[0]
            if len(open_idx) == 0:
                continue
            i0 = int(open_idx[0])
            day_atr = float(atr_[i0])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            gap = float(open_[i0]) - prev["close"]
            if abs(gap) >= self.min_gap_atr * day_atr:
                fade = -1 if gap > 0 else 1
                watch = np.where(day_mask & (mins > RTH_OPEN_MINUTES) & (mins < FILL_FLAT))[0]
                for i in watch:
                    filled = (fade == 1 and close[i] >= prev["close"]) or (
                        fade == -1 and close[i] <= prev["close"]
                    )
                    if filled:
                        break
                    stop_dist = self.stop_atr_mult * day_atr
                    risk = abs(close[i] - prev["close"])
                    if risk <= 0 or stop_dist <= 0:
                        continue
                    entries[i] = fade
                    stops[i] = close[i] - fade * stop_dist
                    targets[i] = prev["close"]
                    break
                continue

            drive = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < DRIVE_END))[0]
            entry = np.where(day_mask & (mins == DRIVE_END))[0]
            if len(drive) == 0 or len(entry) == 0:
                continue
            o0 = float(open_[drive[0]])
            c1 = float(close[drive[-1]])
            rng = float(high[drive].max() - low[drive].min())
            body = abs(c1 - o0)
            if rng <= 0 or body < self.min_drive_atr * day_atr or (body / rng) < MIN_BODY_PCT:
                continue
            direction = 1 if c1 > o0 else -1
            i = int(entry[0])
            stop_dist = self.stop_atr_mult * day_atr
            if stop_dist <= 0:
                continue
            entries[i] = direction
            stops[i] = close[i] - direction * stop_dist
            targets[i] = close[i] + direction * stop_dist

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
