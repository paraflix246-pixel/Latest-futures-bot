"""
Official VWAP reclaim (sprint-1 fills, RTH, day-flat).

Port of the local-hunt `vwap_reclaim` family. Hunt near-miss `vwap_reclaim_4`
(MNQ WF t=1.59 n=167) is a *dense* multi-signal reclaim — not the one-per-day
`am_vwap_reclaim` that already died on this tape.

Sequence, repeatable inside a session:
  1. Close ≥ min_away_atr × prior-day ATR away from RTH VWAP (extension).
  2. A later bar touches VWAP.
  3. Close back on the extension side (reclaim) → enter that direction.

Stop: stop_atr_mult × ATR. Target target_r R. Flatten 15:45.
Optional: first-90-minute cutoff, ADX floor, first-hour bias.

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
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

MIN_AWAY_ATR = 0.15
STOP_ATR_MULT = 0.30
TARGET_R = 1.0
MAX_HOLD_BARS = 36
HOUR_END = RTH_OPEN_MINUTES + 60


class VwapReclaimStrategy:
    name = "vwap_reclaim"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        min_away_atr: float = MIN_AWAY_ATR,
        stop_atr_mult: float = STOP_ATR_MULT,
        target_r: float = TARGET_R,
        entry_end_minutes: int = FLATTEN_1545,
        adx_min: float = 0.0,
        first_hour_bias: bool = False,
        one_per_session: bool = False,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.min_away_atr = float(min_away_atr)
        self.stop_atr_mult = float(stop_atr_mult)
        self.target_r = float(target_r)
        self.entry_end_minutes = int(entry_end_minutes)
        self.adx_min = float(adx_min)
        self.first_hour_bias = bool(first_hour_bias)
        self.one_per_session = bool(one_per_session)
        self.max_hold_bars = int(max_hold_bars)
        self.rth_entry_cutoff_minutes = min(self.entry_end_minutes, FLATTEN_1545)
        self.session_exit_minutes = FLATTEN_1545

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        open_ = df["open"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        adx_px = adx_ind(df["high"], df["low"], df["close"], 14).to_numpy() if self.adx_min > 0 else None
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)
        watch_end = min(self.entry_end_minutes, FLATTEN_1545)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            bias = 0
            if self.first_hour_bias:
                hour = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < HOUR_END))[0]
                if len(hour) == 0:
                    continue
                bias = 1 if close[hour[-1]] > open_[hour[0]] else -1
            watch = np.where(day_mask & (mins >= RTH_OPEN_MINUTES + 15) & (mins < watch_end))[0]
            ext_dir = 0
            touched = False
            for i in watch:
                if np.isnan(vwap[i]) or np.isnan(atr_[i]) or atr_[i] <= 0:
                    continue
                if adx_px is not None and (np.isnan(adx_px[i]) or adx_px[i] < self.adx_min):
                    continue
                away = close[i] - vwap[i]
                band = self.min_away_atr * float(atr_[i])
                if ext_dir == 0 and abs(away) >= band:
                    cand = 1 if away > 0 else -1
                    if bias != 0 and cand != bias:
                        continue
                    ext_dir = cand
                    touched = False
                    continue
                if ext_dir == 0:
                    continue
                if low[i] <= vwap[i] <= high[i]:
                    touched = True
                if not touched:
                    continue
                reclaimed = (ext_dir == 1 and close[i] >= vwap[i]) or (ext_dir == -1 and close[i] <= vwap[i])
                if not reclaimed:
                    continue
                stop_dist = self.stop_atr_mult * float(atr_[i])
                if stop_dist <= 0:
                    ext_dir, touched = 0, False
                    continue
                entries[i] = ext_dir
                stops[i] = close[i] - ext_dir * stop_dist
                targets[i] = close[i] + ext_dir * self.target_r * stop_dist
                ext_dir, touched = 0, False
                if self.one_per_session:
                    break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
