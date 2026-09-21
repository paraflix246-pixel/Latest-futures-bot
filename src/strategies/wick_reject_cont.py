"""
Opening-range wick-reject continuation (RTH, day-flat).

If a post-OR bar wicks beyond the opening range but *closes back inside*,
the failed fade is treated as continuation: enter on the next close that
clears the OR extreme, VWAP-aligned. Stop: OR midpoint. Target 1R.
Flatten 15:45. One signal per session.

Distinct from ORB break (no wick filter) and orb_fail_fade (which fades
the failure instead of fading the fade).

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


class WickRejectContStrategy:
    name = "wick_reject_cont"
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
            pending = 0
            for i in watch:
                if pending == 0:
                    if high[i] > or_high and close[i] < or_high and close[i] >= or_low:
                        pending = 1
                    elif low[i] < or_low and close[i] > or_low and close[i] <= or_high:
                        pending = -1
                    continue
                cleared = (pending == 1 and close[i] > or_high) or (pending == -1 and close[i] < or_low)
                if not cleared:
                    continue
                if self.require_vwap_align:
                    if np.isnan(vwap[i]):
                        continue
                    if pending == 1 and close[i] < vwap[i]:
                        continue
                    if pending == -1 and close[i] > vwap[i]:
                        continue
                risk = abs(close[i] - or_mid)
                if risk <= 0:
                    break
                if pending == 1 and close[i] <= or_mid:
                    continue
                if pending == -1 and close[i] >= or_mid:
                    continue
                entries[i] = pending
                stops[i] = or_mid
                targets[i] = close[i] + pending * self.target_r * risk
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
