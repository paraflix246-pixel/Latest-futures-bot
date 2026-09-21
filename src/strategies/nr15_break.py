"""
Narrow 15-minute range then 5-minute break (RTH, day-flat).

After 10:00, if the last *completed* 15m bar's range is below
`nr_frac` × the 20-bar median of 15m ranges, take the first 5m close
beyond that 15m high/low, VWAP-aligned. Stop: 15m opposite side.
Target 1R. Flatten 15:45. One per session.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.loader import resample_ohlcv
from src.strategies.base import StrategySignals
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

ENTRY_START = 10 * 60
NR_FRAC = 0.65
MAX_HOLD_BARS = 36


class Nr15BreakStrategy:
    name = "nr15_break"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(self, nr_frac: float = NR_FRAC, max_hold_bars: int = MAX_HOLD_BARS):
        self.nr_frac = float(nr_frac)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        df15 = resample_ohlcv(df, "15min")
        rng15 = (df15["high"] - df15["low"]).shift(1)
        med = rng15.rolling(20, min_periods=8).median()
        hi15 = df15["high"].shift(1).reindex(df.index, method="ffill")
        lo15 = df15["low"].shift(1).reindex(df.index, method="ffill")
        nr = (rng15 < self.nr_frac * med).reindex(df.index, method="ffill").fillna(False)
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"])
        holidays = short_session_dates(df)

        entries = pd.Series(0, index=df.index)
        stops = pd.Series(np.nan, index=df.index)
        targets = pd.Series(np.nan, index=df.index)

        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        close = df["close"].to_numpy()
        nr_px = nr.to_numpy()
        hi = hi15.to_numpy()
        lo = lo15.to_numpy()
        vwap_px = vwap.to_numpy()

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            watch = np.where((date_vals == d) & (mins >= ENTRY_START) & (mins < FLATTEN_1545))[0]
            for i in watch:
                if not nr_px[i] or np.isnan(hi[i]) or np.isnan(lo[i]) or hi[i] <= lo[i]:
                    continue
                direction = 0
                if close[i] > hi[i]:
                    direction = 1
                elif close[i] < lo[i]:
                    direction = -1
                if direction == 0:
                    continue
                if not np.isnan(vwap_px[i]):
                    if direction == 1 and close[i] < vwap_px[i]:
                        continue
                    if direction == -1 and close[i] > vwap_px[i]:
                        continue
                stop = lo[i] if direction == 1 else hi[i]
                risk = abs(close[i] - stop)
                if risk <= 0:
                    continue
                entries.iloc[i] = direction
                stops.iloc[i] = stop
                targets.iloc[i] = close[i] + direction * risk
                break

        return StrategySignals(entries=entries, stop_price=stops, target_price=targets)
