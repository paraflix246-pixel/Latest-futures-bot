"""
ORB break → pullback into OR mid / session VWAP → continuation.

Separate from the filtered close-beyond-OR entry. Sequence:

  1. Opening range = first 15 minutes after 09:30 ET.
  2. A close beyond the OR registers the break direction.
  3. Price must then pull back *into* the OR and touch the OR midpoint
     or RTH VWAP (volume-weighted proxy for VP).
  4. A close back in the break direction, still VWAP-aligned, enters.
  5. Stop: opposite OR extreme. Target 1R. Flatten 15:45.

Overnight-expansion and short-session filters match `orb_filtered`.
Same params on MNQ and MES. Paper / backtest only.
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
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

OR_MINUTES = 15
ON_ADR_MULT = 1.5
TARGET_R = 1.0
MAX_HOLD_BARS = 72


class OrbRetraceStrategy:
    name = "orb_retrace"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        or_minutes: int = OR_MINUTES,
        on_adr_mult: float = ON_ADR_MULT,
        target_r: float = TARGET_R,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.or_minutes = or_minutes
        self.on_adr_mult = on_adr_mult
        self.target_r = target_r
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
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
            or_idx = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + self.or_minutes)
            )[0]
            if len(or_idx) == 0:
                continue
            or_high = float(high[or_idx].max())
            or_low = float(low[or_idx].min())
            or_mid = (or_high + or_low) / 2.0
            if or_high <= or_low:
                continue

            watch = np.where(
                day_mask
                & (mins >= RTH_OPEN_MINUTES + self.or_minutes)
                & (mins < FLATTEN_1545)
            )[0]
            brk = 0
            pulled = False
            for i in watch:
                if brk == 0:
                    if close[i] > or_high:
                        brk = 1
                    elif close[i] < or_low:
                        brk = -1
                    continue
                # Pullback into the OR: touch mid or VWAP while inside the range.
                inside = (low[i] <= or_high) and (high[i] >= or_low)
                touch_mid = low[i] <= or_mid <= high[i]
                touch_vwap = (not np.isnan(vwap[i])) and (low[i] <= vwap[i] <= high[i])
                if inside and (touch_mid or touch_vwap):
                    pulled = True
                if not pulled:
                    continue
                if brk == 1 and close[i] > or_mid and (not np.isnan(vwap[i]) and close[i] > vwap[i]):
                    risk = close[i] - or_low
                    if risk > 0:
                        entries[i] = 1
                        stops[i] = or_low
                        targets[i] = close[i] + self.target_r * risk
                    break
                if brk == -1 and close[i] < or_mid and (not np.isnan(vwap[i]) and close[i] < vwap[i]):
                    risk = or_high - close[i]
                    if risk > 0:
                        entries[i] = -1
                        stops[i] = or_high
                        targets[i] = close[i] - self.target_r * risk
                    break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
