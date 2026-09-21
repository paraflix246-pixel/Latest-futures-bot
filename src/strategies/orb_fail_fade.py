"""
Failed opening-range fade (RTH, day-flat).

If price closes beyond the OR and later closes back through the OR
midpoint, fade the failure. Stop: beyond the failed OR extreme.
Target 1R. Flatten 15:45. Distinct from ORB retrace continuation.

Paper / backtest only. No live trading.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

OR_MINUTES = 15
ENTRY_WINDOW = 150
TARGET_R = 1.0
MAX_HOLD_BARS = 48


class OrbFailFadeStrategy:
    name = "orb_fail_fade"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        or_minutes: int = OR_MINUTES,
        entry_window_minutes: int = ENTRY_WINDOW,
        target_r: float = TARGET_R,
        require_vwap_align: bool = True,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.or_minutes = int(or_minutes)
        self.entry_window_minutes = int(entry_window_minutes)
        self.target_r = float(target_r)
        self.require_vwap_align = bool(require_vwap_align)
        self.max_hold_bars = int(max_hold_bars)
        self.rth_entry_cutoff_minutes = min(
            RTH_OPEN_MINUTES + self.or_minutes + self.entry_window_minutes, FLATTEN_1545
        )

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        holidays = short_session_dates(df)
        watch_end = self.rth_entry_cutoff_minutes

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            or_idx = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + self.or_minutes)
            )[0]
            if len(or_idx) == 0:
                continue
            or_high = float(high[or_idx].max())
            or_low = float(low[or_idx].min())
            or_mid = 0.5 * (or_high + or_low)
            if or_high <= or_low:
                continue
            watch = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES + self.or_minutes) & (mins < watch_end)
            )[0]
            brk = 0
            extreme = or_mid
            for i in watch:
                if brk == 0:
                    if close[i] > or_high:
                        brk, extreme = 1, float(high[i])
                    elif close[i] < or_low:
                        brk, extreme = -1, float(low[i])
                    continue
                failed = (brk == 1 and close[i] < or_mid) or (brk == -1 and close[i] > or_mid)
                if not failed:
                    continue
                if self.require_vwap_align:
                    if np.isnan(vwap[i]):
                        continue
                    if brk == 1 and close[i] > vwap[i]:
                        continue
                    if brk == -1 and close[i] < vwap[i]:
                        continue
                fade = -brk
                stop = extreme if brk == 1 else extreme
                if fade == -1:
                    stop = max(extreme, or_high)
                    risk = stop - close[i]
                else:
                    stop = min(extreme, or_low)
                    risk = close[i] - stop
                if risk <= 0:
                    break
                entries[i] = fade
                stops[i] = stop
                targets[i] = close[i] + fade * self.target_r * risk
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
