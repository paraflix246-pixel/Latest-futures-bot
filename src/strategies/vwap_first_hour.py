"""
First-hour VWAP reclaim / fail (RTH only). Entries *during* 09:30–10:30 ET.

Cycle-3 `vwap_hour_reclaim_fail` waited until *after* 10:30. This module
trades the first hour itself:

  Warmup: first `warmup_minutes` of cash (default 10m) set bias from the
          open-drive (warmup close vs RTH open).
  Reclaim: later first-hour bar trades through RTH VWAP and closes back on
           the bias side → enter with the bias.
  Fail:    first-hour extension away from VWAP by `min_away_atr` × ATR, then
           a close back through VWAP → fade against the extension.

Stop: `stop_atr_mult` × prior-day ATR. Target 1R. Flatten 15:45 ET.
Skip short sessions. One signal per session. Paper / backtest only.
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
WARMUP_MINUTES = 10
STOP_ATR_MULT = 0.35
MIN_AWAY_ATR = 0.08
MAX_HOLD_BARS = 72


class VwapFirstHourStrategy:
    name = "vwap_fh_reclaim"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        stop_atr_mult: float = STOP_ATR_MULT,
        min_away_atr: float = MIN_AWAY_ATR,
        warmup_minutes: int = WARMUP_MINUTES,
        max_hold_bars: int = MAX_HOLD_BARS,
        allow_reclaim: bool = True,
        allow_fail: bool = True,
    ):
        self.stop_atr_mult = float(stop_atr_mult)
        self.min_away_atr = float(min_away_atr)
        self.warmup_minutes = int(warmup_minutes)
        self.max_hold_bars = int(max_hold_bars)
        self.allow_reclaim = bool(allow_reclaim)
        self.allow_fail = bool(allow_fail)

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
        warmup_end = RTH_OPEN_MINUTES + self.warmup_minutes

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            warmup = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < warmup_end))[0]
            trade = np.where(day_mask & (mins >= warmup_end) & (mins < HOUR_END))[0]
            if len(warmup) == 0 or len(trade) == 0:
                continue
            bias = 1 if float(close[warmup[-1]]) > float(open_[warmup[0]]) else -1
            if bias == 0:
                continue
            extended = False
            for i in trade:
                if np.isnan(vwap[i]):
                    continue
                day_atr = float(atr_[i])
                if np.isnan(day_atr) or day_atr <= 0:
                    continue
                stop_dist = self.stop_atr_mult * day_atr
                away = self.min_away_atr * day_atr
                if self.allow_fail:
                    if (bias == 1 and close[i] >= vwap[i] + away) or (
                        bias == -1 and close[i] <= vwap[i] - away
                    ):
                        extended = True
                    elif extended:
                        failed = (bias == 1 and close[i] < vwap[i]) or (
                            bias == -1 and close[i] > vwap[i]
                        )
                        if failed:
                            fade = -bias
                            entries[i] = fade
                            stops[i] = close[i] - fade * stop_dist
                            targets[i] = close[i] + fade * stop_dist
                            break
                if self.allow_reclaim and low[i] <= vwap[i] <= high[i]:
                    reclaimed = (bias == 1 and close[i] >= vwap[i]) or (
                        bias == -1 and close[i] <= vwap[i]
                    )
                    if reclaimed:
                        entries[i] = bias
                        stops[i] = close[i] - bias * stop_dist
                        targets[i] = close[i] + bias * stop_dist
                        break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
