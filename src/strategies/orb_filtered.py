"""
Research-backed filtered opening-range breakout (RTH, day-flat).

Raw ORB is treated as a coin-flip. This module stacks ≥3 filters and
requires a *close* beyond the OR (not a wick pierce).

  OR: first `or_minutes` after 09:30 ET (default 15; 5 and 30 are
      sensitivity variants, not independently re-fit per symbol).
  Entry: first close beyond OR high/low. Optional `retest`: wait for a
      pullback that touches the broken OR level, then continue.
  Filters (all on by default — stack of 4):
    1. Session VWAP alignment (long only above VWAP / short below)
    2. Overnight range ≤ `on_adr_mult` × 20-day average daily range
    3. Breakout-bar volume > rolling SMA(volume)
    4. Skip short/holiday RTH sessions (<60 five-minute RTH bars)
  Stop: OR midpoint (back inside the range). Target 1R.
  Clock: flatten 15:45 ET. One signal per session. No overnight.

Same constructor params are used on MNQ and MES. Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.indicators import sma
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
VOLUME_PERIOD = 20
VOLUME_MULT = 1.0
TARGET_R = 1.0
MAX_HOLD_BARS = 72


class OrbFilteredStrategy:
    name = "orb_filtered"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        or_minutes: int = OR_MINUTES,
        retest: bool = False,
        on_adr_mult: float = ON_ADR_MULT,
        volume_mult: float = VOLUME_MULT,
        target_r: float = TARGET_R,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.or_minutes = or_minutes
        self.retest = retest
        self.on_adr_mult = on_adr_mult
        self.volume_mult = volume_mult
        self.target_r = target_r
        self.max_hold_bars = max_hold_bars
        if or_minutes != OR_MINUTES:
            self.name = f"orb_filtered_{or_minutes}"
        if retest:
            self.name = f"{self.name}_retest" if or_minutes != OR_MINUTES else "orb_filtered_retest"

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        volume = df["volume"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        vol_avg = sma(df["volume"], VOLUME_PERIOD).to_numpy()
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

            pending_dir = 0
            pending_stop = or_mid
            issued = False
            for i in watch:
                if issued:
                    break
                vol_ok = (not np.isnan(vol_avg[i])) and volume[i] > self.volume_mult * vol_avg[i]
                vwap_i = vwap[i]
                if np.isnan(vwap_i):
                    continue

                if pending_dir == 0:
                    if close[i] > or_high and vol_ok and close[i] > vwap_i:
                        if not self.retest:
                            issued = _emit(entries, stops, targets, close, i, 1, or_mid, self.target_r)
                        else:
                            pending_dir, pending_stop = 1, or_high
                    elif close[i] < or_low and vol_ok and close[i] < vwap_i:
                        if not self.retest:
                            issued = _emit(entries, stops, targets, close, i, -1, or_mid, self.target_r)
                        else:
                            pending_dir, pending_stop = -1, or_low
                    continue

                # Retest: touch the broken OR level, then close back in break direction.
                if pending_dir == 1 and low[i] <= pending_stop <= high[i] and close[i] >= pending_stop and close[i] > vwap_i:
                    issued = _emit(entries, stops, targets, close, i, 1, or_mid, self.target_r)
                elif pending_dir == -1 and low[i] <= pending_stop <= high[i] and close[i] <= pending_stop and close[i] < vwap_i:
                    issued = _emit(entries, stops, targets, close, i, -1, or_mid, self.target_r)

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )


def _emit(entries, stops, targets, close, i, direction, stop, target_r) -> bool:
    risk = abs(close[i] - stop)
    if risk <= 0:
        return False
    if direction == 1 and close[i] <= stop:
        return False
    if direction == -1 and close[i] >= stop:
        return False
    entries[i] = direction
    stops[i] = stop
    targets[i] = close[i] + direction * target_r * risk
    return True
