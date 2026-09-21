"""
Delayed overnight high/low break (RTH, day-flat).

Skip the cash-open spike. After 10:00, take the first close beyond the
overnight high (long) or overnight low (short) with volume vs the first
30 minutes of RTH and VWAP alignment. Stop: stop_atr_mult × ATR.
Target 1R. Flatten 15:45. One signal per session.

Not an opening drive and not overnight-inventory VWAP pullback.

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
    overnight_hl_by_date,
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

ENTRY_START = 10 * 60
VOLUME_MULT = 1.2
STOP_ATR = 0.30
MAX_HOLD_BARS = 48


class OnhOnlBreakStrategy:
    name = "onh_onl_break"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        volume_mult: float = VOLUME_MULT,
        stop_atr_mult: float = STOP_ATR,
        entry_start_minutes: int = ENTRY_START,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.volume_mult = float(volume_mult)
        self.stop_atr_mult = float(stop_atr_mult)
        self.entry_start_minutes = int(entry_start_minutes)
        self.max_hold_bars = int(max_hold_bars)

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
        on_hl = overnight_hl_by_date(df)
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            hl = on_hl.get(d)
            if not hl:
                continue
            onh, onl = hl["high"], hl["low"]
            if onh <= onl:
                continue
            day_mask = date_vals == d
            first30 = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + 30)
            )[0]
            watch = np.where(
                day_mask & (mins >= self.entry_start_minutes) & (mins < FLATTEN_1545)
            )[0]
            if len(first30) == 0 or len(watch) == 0:
                continue
            vol_base = float(volume[first30].mean())
            if vol_base <= 0:
                continue
            for i in watch:
                day_atr = float(atr_[i])
                if np.isnan(day_atr) or day_atr <= 0:
                    continue
                if volume[i] < self.volume_mult * vol_base:
                    continue
                if np.isnan(vwap[i]):
                    continue
                direction = 0
                if close[i] > onh and close[i] > vwap[i]:
                    direction = 1
                elif close[i] < onl and close[i] < vwap[i]:
                    direction = -1
                if direction == 0:
                    continue
                stop_dist = self.stop_atr_mult * day_atr
                if stop_dist <= 0:
                    break
                entries[i] = direction
                stops[i] = close[i] - direction * stop_dist
                targets[i] = close[i] + direction * stop_dist
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
