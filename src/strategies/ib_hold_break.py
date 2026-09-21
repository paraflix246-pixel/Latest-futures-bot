"""
Confirmed initial-balance hold-break (RTH, day-flat).

Unlike `ib_extension` (first close beyond IB), wait for `hold_bars`
consecutive closes *outside* the IB, then enter that direction.
Stop: IB midpoint. Target 1R. Flatten 15:45. One per session.

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

IB_MINUTES = 60
HOLD_BARS = 3
MAX_HOLD_BARS = 48


class IbHoldBreakStrategy:
    name = "ib_hold_break"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        ib_minutes: int = IB_MINUTES,
        hold_bars: int = HOLD_BARS,
        require_vwap_align: bool = True,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.ib_minutes = int(ib_minutes)
        self.hold_bars = int(hold_bars)
        self.require_vwap_align = bool(require_vwap_align)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"]).to_numpy()
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            ib_idx = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + self.ib_minutes)
            )[0]
            watch = np.where(
                day_mask
                & (mins >= RTH_OPEN_MINUTES + self.ib_minutes)
                & (mins < FLATTEN_1545)
            )[0]
            if len(ib_idx) == 0 or len(watch) == 0:
                continue
            ib_high = float(high[ib_idx].max())
            ib_low = float(low[ib_idx].min())
            ib_mid = 0.5 * (ib_high + ib_low)
            if ib_high <= ib_low:
                continue
            run_dir = 0
            run_len = 0
            for i in watch:
                if close[i] > ib_high:
                    side = 1
                elif close[i] < ib_low:
                    side = -1
                else:
                    run_dir, run_len = 0, 0
                    continue
                if side == run_dir:
                    run_len += 1
                else:
                    run_dir, run_len = side, 1
                if run_len < self.hold_bars:
                    continue
                if self.require_vwap_align:
                    if np.isnan(vwap[i]):
                        continue
                    if side == 1 and close[i] < vwap[i]:
                        continue
                    if side == -1 and close[i] > vwap[i]:
                        continue
                risk = abs(close[i] - ib_mid)
                if risk <= 0:
                    break
                if side == 1 and close[i] <= ib_mid:
                    continue
                if side == -1 and close[i] >= ib_mid:
                    continue
                entries[i] = side
                stops[i] = ib_mid
                targets[i] = close[i] + side * risk
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
