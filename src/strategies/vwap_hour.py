"""
First-hour VWAP reclaim *and* fail (one module, two setups).

First hour = 09:30–10:30 ET.

  Reclaim: hour close vs open sets bias. After 10:30, first VWAP touch
           that closes back on the bias side enters with the bias.
  Fail:    if the first hour closes *away* from VWAP (extension) and
           later price closes back through VWAP against that extension,
           fade (mean-revert toward VWAP).

Stop: `stop_atr_mult` × prior-day ATR. Target 1R. Flatten 15:45.
Skip short sessions. One signal per session. Same params on MNQ/MES.

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
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

HOUR_END = RTH_OPEN_MINUTES + 60
STOP_ATR_MULT = 0.35
MAX_HOLD_BARS = 60


class VwapHourReclaimFailStrategy:
    name = "vwap_hour_reclaim_fail"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
        allow_reclaim: bool = True,
        allow_fail: bool = True,
    ):
        self.stop_atr_mult = stop_atr_mult
        self.max_hold_bars = max_hold_bars
        self.allow_reclaim = allow_reclaim
        self.allow_fail = allow_fail

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        open_ = df["open"].to_numpy()
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
            h_open = float(open_[hour[0]])
            h_close = float(close[hour[-1]])
            h_vwap = float(vwap[hour[-1]]) if not np.isnan(vwap[hour[-1]]) else np.nan
            bias = 1 if h_close > h_open else -1
            extended = (not np.isnan(h_vwap)) and (
                (bias == 1 and h_close > h_vwap) or (bias == -1 and h_close < h_vwap)
            )
            watch = np.where(day_mask & (mins >= HOUR_END) & (mins < FLATTEN_1545))[0]
            touched = False
            for i in watch:
                if np.isnan(vwap[i]):
                    continue
                day_atr = float(atr_[i])
                if np.isnan(day_atr) or day_atr <= 0:
                    continue
                stop_dist = self.stop_atr_mult * day_atr
                if low[i] <= vwap[i] <= high[i]:
                    touched = True

                if self.allow_reclaim and touched:
                    reclaimed = (bias == 1 and close[i] >= vwap[i]) or (bias == -1 and close[i] <= vwap[i])
                    if reclaimed:
                        entries[i] = bias
                        stops[i] = close[i] - bias * stop_dist
                        targets[i] = close[i] + bias * stop_dist
                        break

                if self.allow_fail and extended:
                    failed = (bias == 1 and close[i] < vwap[i]) or (bias == -1 and close[i] > vwap[i])
                    if failed:
                        fade = -bias
                        entries[i] = fade
                        stops[i] = close[i] - fade * stop_dist
                        targets[i] = close[i] + fade * stop_dist
                        break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
