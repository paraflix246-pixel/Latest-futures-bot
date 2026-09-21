"""
Overnight-range fill/go with a confirmation bar (not the cycle-12 immediate fill).

  Fill: RTH open inside (ONL, ONH). Wait for a further excursion away from
        overnight mid of `confirm_atr` × ATR, then the first close back
        toward mid enters the fade. Target = overnight mid.
  Go:   RTH open outside ONH/ONL. First 15m must close still outside *and*
        in the breakout direction; enter at 09:45.

Stop: `stop_atr_mult` × ATR. Flatten 15:45. One signal per session.

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
    overnight_hl_by_date,
    prior_day_atr,
    session_clock,
    short_session_dates,
)

DRIVE_END = RTH_OPEN_MINUTES + 15
STOP_ATR_MULT = 0.35
CONFIRM_ATR = 0.08
MAX_HOLD_BARS = 72


class GapOnConfirmStrategy:
    name = "gap_on_confirm"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        stop_atr_mult: float = STOP_ATR_MULT,
        confirm_atr: float = CONFIRM_ATR,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.stop_atr_mult = float(stop_atr_mult)
        self.confirm_atr = float(confirm_atr)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        open_ = df["open"].to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
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
            onh, onl = float(hl["high"]), float(hl["low"])
            if onh <= onl:
                continue
            day_mask = date_vals == d
            open_idx = np.where(day_mask & (mins == RTH_OPEN_MINUTES))[0]
            if len(open_idx) == 0:
                open_idx = np.where(
                    day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + 5)
                )[0]
            if len(open_idx) == 0:
                continue
            i0 = int(open_idx[0])
            day_atr = float(atr_[i0])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            stop_dist = self.stop_atr_mult * day_atr
            rth_open = float(open_[i0])
            mid = 0.5 * (onh + onl)

            if onl < rth_open < onh:
                fade = 1 if rth_open < mid else -1
                need = self.confirm_atr * day_atr
                stretched = False
                watch = np.where(day_mask & (mins > RTH_OPEN_MINUTES) & (mins < FLATTEN_1545))[0]
                for i in watch:
                    if fade == -1 and high[i] >= rth_open + need:
                        stretched = True
                    if fade == 1 and low[i] <= rth_open - need:
                        stretched = True
                    if not stretched:
                        continue
                    toward = (fade == -1 and close[i] < high[i] and close[i] <= rth_open) or (
                        fade == 1 and close[i] > low[i] and close[i] >= rth_open
                    )
                    if not toward:
                        continue
                    entries[i] = fade
                    stops[i] = close[i] - fade * stop_dist
                    targets[i] = mid
                    break
                continue

            drive = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < DRIVE_END))[0]
            entry = np.where(day_mask & (mins == DRIVE_END))[0]
            if len(drive) == 0 or len(entry) == 0:
                continue
            c15 = float(close[drive[-1]])
            i = int(entry[0])
            if rth_open >= onh and c15 >= onh and c15 > float(open_[drive[0]]):
                direction = 1
            elif rth_open <= onl and c15 <= onl and c15 < float(open_[drive[0]]):
                direction = -1
            else:
                continue
            entries[i] = direction
            stops[i] = close[i] - direction * stop_dist
            targets[i] = close[i] + direction * stop_dist

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
