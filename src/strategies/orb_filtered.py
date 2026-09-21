"""
Official filtered opening-range breakout (sprint-1 fills, RTH, day-flat).

Port of the local-hunt `filtered_orb` family. Hunt winner `filtered_orb_2`
(MES provisional):

  or_minutes=15
  entry_window_minutes=120
  volume_mult=1.3
  require_vwap_align=True
  skip_inside_overnight=True
  require_retest=False
  target_r=1.0

Rules:
  OR = first `or_minutes` after 09:30 ET.
  Entry window = [OR end, OR end + entry_window_minutes) in minutes since
  the cash open (same convention as `OpeningRangeBreakoutStrategy`).
  Breakout = close beyond OR, volume > volume_mult × OR-average volume.
  VWAP alignment optional. Skip inside-overnight (overnight range contained
  in prior RTH range). Optional retest of the broken OR level.
  Stop: OR midpoint. Target `target_r` R. Flatten 15:45. One signal / session.

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
    adr20_by_date,
    overnight_hl_by_date,
    overnight_range_by_date,
    prior_day_atr,
    prior_rth_hlc_by_date,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

OR_MINUTES = 15
ENTRY_WINDOW_MINUTES = 120
VOLUME_MULT = 1.3
TARGET_R = 1.0
ON_ADR_MULT = 1.5
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
        entry_window_minutes: int = ENTRY_WINDOW_MINUTES,
        volume_mult: float = VOLUME_MULT,
        require_vwap_align: bool = True,
        skip_inside_overnight: bool = True,
        skip_expansion: bool = False,
        on_adr_mult: float = ON_ADR_MULT,
        require_retest: bool = False,
        retest: bool | None = None,
        target_r: float = TARGET_R,
        stop_mode: str = "mid",
        stop_atr_mult: float = 0.25,
        adx_min: float = 0.0,
        max_hold_bars: int = MAX_HOLD_BARS,
        entry_end_minutes: int | None = None,
    ):
        self.or_minutes = int(or_minutes)
        self.entry_window_minutes = int(entry_window_minutes)
        self.volume_mult = float(volume_mult)
        self.require_vwap_align = bool(require_vwap_align)
        self.skip_inside_overnight = bool(skip_inside_overnight)
        self.skip_expansion = bool(skip_expansion)
        self.on_adr_mult = float(on_adr_mult)
        self.require_retest = bool(require_retest if retest is None else retest)
        self.target_r = float(target_r)
        self.stop_mode = str(stop_mode)
        self.stop_atr_mult = float(stop_atr_mult)
        self.adx_min = float(adx_min)
        self.max_hold_bars = int(max_hold_bars)
        # Absolute clock cutoff; None → derive from entry_window_minutes.
        if entry_end_minutes is not None:
            self.entry_end_minutes = int(entry_end_minutes)
        else:
            self.entry_end_minutes = RTH_OPEN_MINUTES + self.or_minutes + self.entry_window_minutes
        self.rth_entry_cutoff_minutes = min(self.entry_end_minutes, FLATTEN_1545)
        self.retest = self.require_retest
        if self.or_minutes != OR_MINUTES:
            self.name = f"orb_filtered_{self.or_minutes}"
        if self.require_retest:
            self.name = f"{self.name}_retest"

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
        on_range = overnight_range_by_date(df)
        prior = prior_rth_hlc_by_date(df)
        adr = adr20_by_date(df)
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        watch_end = min(self.entry_end_minutes, FLATTEN_1545)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            if self.skip_inside_overnight:
                hl = on_hl.get(d)
                prev = prior.get(d)
                if hl and prev and hl["high"] <= prev["high"] and hl["low"] >= prev["low"]:
                    continue
            if self.skip_expansion:
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
            or_vol = float(volume[or_idx].mean())
            if or_high <= or_low or or_vol <= 0:
                continue

            watch = np.where(
                day_mask
                & (mins >= RTH_OPEN_MINUTES + self.or_minutes)
                & (mins < watch_end)
            )[0]

            pending_dir = 0
            pending_level = or_mid
            issued = False
            for i in watch:
                if issued:
                    break
                if adx_px is not None and (np.isnan(adx_px[i]) or adx_px[i] < self.adx_min):
                    continue
                vol_ok = volume[i] > self.volume_mult * or_vol
                vwap_i = vwap[i]
                if self.require_vwap_align and np.isnan(vwap_i):
                    continue

                def _aligned(direction: int) -> bool:
                    if not self.require_vwap_align:
                        return True
                    return (direction == 1 and close[i] > vwap_i) or (direction == -1 and close[i] < vwap_i)

                if pending_dir == 0:
                    if close[i] > or_high and vol_ok and _aligned(1):
                        if not self.require_retest:
                            issued = self._emit(entries, stops, targets, close, atr_, i, 1, or_high, or_low, or_mid)
                        else:
                            pending_dir, pending_level = 1, or_high
                    elif close[i] < or_low and vol_ok and _aligned(-1):
                        if not self.require_retest:
                            issued = self._emit(entries, stops, targets, close, atr_, i, -1, or_high, or_low, or_mid)
                        else:
                            pending_dir, pending_level = -1, or_low
                    continue

                if pending_dir == 1 and low[i] <= pending_level <= high[i] and close[i] >= pending_level and _aligned(1):
                    issued = self._emit(entries, stops, targets, close, atr_, i, 1, or_high, or_low, or_mid)
                elif pending_dir == -1 and low[i] <= pending_level <= high[i] and close[i] <= pending_level and _aligned(-1):
                    issued = self._emit(entries, stops, targets, close, atr_, i, -1, or_high, or_low, or_mid)

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )

    def _emit(self, entries, stops, targets, close, atr_, i, direction, or_high, or_low, or_mid) -> bool:
        if self.stop_mode == "opposite":
            stop = or_low if direction == 1 else or_high
        elif self.stop_mode == "atr":
            day_atr = float(atr_[i])
            if np.isnan(day_atr) or day_atr <= 0:
                return False
            stop = close[i] - direction * self.stop_atr_mult * day_atr
        else:
            stop = or_mid
        risk = abs(close[i] - stop)
        if risk <= 0:
            return False
        if direction == 1 and close[i] <= stop:
            return False
        if direction == -1 and close[i] >= stop:
            return False
        entries[i] = direction
        stops[i] = stop
        targets[i] = close[i] + direction * self.target_r * risk
        return True


class MesSens7Strategy(OrbFilteredStrategy):
    """Locked local-sprint-4 MES winner. Paper / backtest only. Soft holdout."""

    name = "s2_mes_sens_7"

    def __init__(self, **kwargs):
        params = dict(
            or_minutes=15,
            entry_window_minutes=130,
            volume_mult=1.4,
            require_vwap_align=True,
            skip_inside_overnight=True,
            require_retest=False,
            target_r=1.0,
            stop_mode="mid",
        )
        params.update(kwargs)
        super().__init__(**params)
        self.name = "s2_mes_sens_7"
