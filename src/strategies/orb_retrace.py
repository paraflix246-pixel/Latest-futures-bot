"""
ORB break → pullback into OR mid / session VWAP → continuation.

Official port of the local-hunt `orb_retrace` family, including
`s2_orb_retrace_7` (MNQ provisional PASS):

  or_minutes=10, retrace to OR mid, entry_window=150,
  volume_mult=1.0 vs OR-average volume, VWAP align,
  skip_inside_overnight=False, stop at mid, target 2.0R.

Sequence:
  1. Opening range = first `or_minutes` after 09:30 ET.
  2. A close beyond the OR registers the break direction.
  3. Price pulls back into the OR and touches the midpoint (and/or VWAP).
  4. A close back in the break direction, still VWAP-aligned, enters.
  5. Stop: OR mid (or opposite / ATR). Target target_r R. Flatten 15:45.

Paper / backtest only. No live trading.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.indicators import adx as adx_ind
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    overnight_hl_by_date,
    prior_day_atr,
    prior_rth_hlc_by_date,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

OR_MINUTES = 15
ENTRY_WINDOW_MINUTES = 180
TARGET_R = 1.0
VOLUME_MULT = 0.0
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
        entry_window_minutes: int = ENTRY_WINDOW_MINUTES,
        target_r: float = TARGET_R,
        skip_inside_overnight: bool = True,
        require_vwap_align: bool = True,
        extended: bool = False,
        stop_mode: str = "opposite",
        stop_atr_mult: float = 0.25,
        adx_min: float = 0.0,
        volume_mult: float = VOLUME_MULT,
        retrace_to: str = "mid_or_vwap",
        max_hold_bars: int = MAX_HOLD_BARS,
        entry_end_minutes: int | None = None,
    ):
        self.or_minutes = int(or_minutes)
        self.entry_window_minutes = int(entry_window_minutes)
        self.target_r = float(target_r)
        self.skip_inside_overnight = bool(skip_inside_overnight)
        self.require_vwap_align = bool(require_vwap_align)
        self.extended = bool(extended)
        self.stop_mode = str(stop_mode)
        self.stop_atr_mult = float(stop_atr_mult)
        self.adx_min = float(adx_min)
        self.volume_mult = float(volume_mult)
        self.retrace_to = str(retrace_to)
        self.max_hold_bars = int(max_hold_bars)
        if entry_end_minutes is not None:
            self.entry_end_minutes = int(entry_end_minutes)
        else:
            self.entry_end_minutes = RTH_OPEN_MINUTES + self.or_minutes + self.entry_window_minutes
        self.rth_entry_cutoff_minutes = min(self.entry_end_minutes, FLATTEN_1545)
        if self.extended:
            self.name = "orb_retrace_x"
        if self.or_minutes == 10 and abs(self.target_r - 2.0) < 1e-9 and self.stop_mode == "mid":
            self.name = "s2_orb_retrace_7"

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        volume = df["volume"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        adx_px = adx_ind(df["high"], df["low"], df["close"], 14).to_numpy() if self.adx_min > 0 else None
        on_hl = overnight_hl_by_date(df)
        prior = prior_rth_hlc_by_date(df)
        holidays = short_session_dates(df)
        watch_end = min(self.entry_end_minutes, FLATTEN_1545)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            if self.skip_inside_overnight:
                hl = on_hl.get(d)
                prev = prior.get(d)
                if hl and prev and hl["high"] <= prev["high"] and hl["low"] >= prev["low"]:
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
            or_vol = float(volume[or_idx].mean()) if len(or_idx) else 0.0
            if or_high <= or_low:
                continue

            watch = np.where(
                day_mask
                & (mins >= RTH_OPEN_MINUTES + self.or_minutes)
                & (mins < watch_end)
            )[0]
            brk = 0
            pulled = False
            for i in watch:
                if adx_px is not None and (np.isnan(adx_px[i]) or adx_px[i] < self.adx_min):
                    continue
                if brk == 0:
                    if close[i] > or_high:
                        brk = 1
                    elif close[i] < or_low:
                        brk = -1
                    continue
                inside = (low[i] <= or_high) and (high[i] >= or_low)
                touch_mid = low[i] <= or_mid <= high[i]
                touch_vwap = (not np.isnan(vwap[i])) and (low[i] <= vwap[i] <= high[i])
                if self.retrace_to == "mid":
                    if inside and touch_mid:
                        pulled = True
                elif self.extended:
                    if touch_vwap or (inside and touch_mid):
                        pulled = True
                else:
                    if inside and (touch_mid or touch_vwap):
                        pulled = True
                if not pulled:
                    continue
                if self.volume_mult > 0 and (or_vol <= 0 or volume[i] < self.volume_mult * or_vol):
                    continue
                aligned = True
                if self.require_vwap_align:
                    if np.isnan(vwap[i]):
                        continue
                    aligned = (brk == 1 and close[i] > vwap[i]) or (brk == -1 and close[i] < vwap[i])
                resume = (brk == 1 and close[i] > or_mid) or (brk == -1 and close[i] < or_mid)
                if not (resume and aligned):
                    continue
                if self.stop_mode == "atr":
                    day_atr = float(atr_[i])
                    if np.isnan(day_atr) or day_atr <= 0:
                        break
                    stop = close[i] - brk * self.stop_atr_mult * day_atr
                elif self.stop_mode == "mid":
                    stop = or_mid
                else:
                    stop = or_low if brk == 1 else or_high
                risk = abs(close[i] - stop)
                if risk <= 0:
                    break
                entries[i] = brk
                stops[i] = stop
                targets[i] = close[i] + brk * self.target_r * risk
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
