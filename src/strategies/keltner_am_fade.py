"""
AM Keltner fade toward VWAP (RTH, day-flat).

After 10:00 and before 12:00, if close is outside the Keltner channel
(EMA20 ± keltner_mult × ATR), fade toward RTH VWAP. Stop: keltner extreme
plus a small ATR buffer. Flatten 15:45. One per session.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.indicators import keltner_channels
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

ENTRY_START = 10 * 60
ENTRY_END = 12 * 60
KELTNER_MULT = 1.5
MAX_HOLD_BARS = 36


class KeltnerAmFadeStrategy:
    name = "keltner_am_fade"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = ENTRY_END
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        keltner_mult: float = KELTNER_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.keltner_mult = float(keltner_mult)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        upper, _mid, lower = keltner_channels(df["high"], df["low"], df["close"], 20, self.keltner_mult)
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"])
        atr_ = prior_day_atr(df, dates)
        holidays = short_session_dates(df)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        close = df["close"].to_numpy()
        up = upper.to_numpy()
        lo = lower.to_numpy()
        vw = vwap.to_numpy()
        atrp = atr_.to_numpy()

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            watch = np.where((date_vals == d) & (mins >= ENTRY_START) & (mins < ENTRY_END))[0]
            for i in watch:
                if np.isnan(up[i]) or np.isnan(lo[i]) or np.isnan(vw[i]) or np.isnan(atrp[i]) or atrp[i] <= 0:
                    continue
                if close[i] > up[i]:
                    fade = -1
                    stop = close[i] + 0.25 * atrp[i]
                elif close[i] < lo[i]:
                    fade = 1
                    stop = close[i] - 0.25 * atrp[i]
                else:
                    continue
                risk = abs(close[i] - stop)
                if risk <= 0:
                    continue
                entries[i] = fade
                stops[i] = stop
                targets[i] = vw[i]
                break
        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
