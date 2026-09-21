"""
First-hour extreme reversal after 10:30 (RTH, day-flat).

If the first cash hour (09:30–10:30) is directional versus VWAP and the
first post-10:30 close crosses back through VWAP *against* that extension,
fade toward VWAP.

Stop: first-hour extreme (or ATR pad if the extreme is on the wrong side).
Target 1R. Flatten 13:00. Skip short sessions. One signal per session.

Paper / backtest only. Distinct from `vwap_hour_reclaim_fail` (no reclaim
leg; fade-only; earlier flatten).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import (
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

HOUR_END = RTH_OPEN_MINUTES + 60
FLATTEN_MINUTES = 13 * 60
STOP_ATR_MULT = 0.20
MAX_HOLD_BARS = 30


class MorningReversalStrategy:
    name = "morning_reversal"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_MINUTES
    session_exit_minutes = FLATTEN_MINUTES
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.stop_atr_mult = stop_atr_mult
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
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            hour = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < HOUR_END))[0]
            if len(hour) == 0:
                continue
            h_high = float(high[hour].max())
            h_low = float(low[hour].min())
            h_close = float(close[hour[-1]])
            h_vwap = float(vwap[hour[-1]]) if not np.isnan(vwap[hour[-1]]) else np.nan
            if np.isnan(h_vwap):
                continue
            if h_close > h_vwap:
                fade, extreme = -1, h_high
            elif h_close < h_vwap:
                fade, extreme = 1, h_low
            else:
                continue
            watch = np.where(day_mask & (mins >= HOUR_END) & (mins < FLATTEN_MINUTES))[0]
            for i in watch:
                if np.isnan(vwap[i]) or np.isnan(atr_[i]) or atr_[i] <= 0:
                    continue
                crossed = (fade == -1 and close[i] < vwap[i]) or (fade == 1 and close[i] > vwap[i])
                if not crossed:
                    continue
                pad = self.stop_atr_mult * float(atr_[i])
                if fade == -1:
                    stop = max(extreme, close[i]) + pad
                    risk = stop - close[i]
                else:
                    stop = min(extreme, close[i]) - pad
                    risk = close[i] - stop
                if risk <= 0:
                    continue
                entries[i] = fade
                stops[i] = stop
                targets[i] = close[i] + fade * risk
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
