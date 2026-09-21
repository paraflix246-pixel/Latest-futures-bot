"""
Late-morning VWAP hold: three consecutive closes on one side of VWAP.

After 11:00 ET, if `hold_bars` consecutive 5m closes sit on the same side
of RTH VWAP and |close − VWAP| ≥ min_away_atr × ATR, enter with that side.
Stop: stop_atr_mult × ATR. Target 1R. Flatten 15:45. One signal per session.

Not the cycle-5 three_bar_vwap_fade (that faded; this continues).

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

ENTRY_START = 11 * 60
HOLD_BARS = 3
MIN_AWAY_ATR = 0.12
STOP_ATR_MULT = 0.30
MAX_HOLD_BARS = 54


class VwapHoldLateStrategy:
    name = "vwap_hold_late"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        hold_bars: int = HOLD_BARS,
        min_away_atr: float = MIN_AWAY_ATR,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.hold_bars = int(hold_bars)
        self.min_away_atr = float(min_away_atr)
        self.stop_atr_mult = float(stop_atr_mult)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
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
            watch = np.where(
                (date_vals == d) & (mins >= ENTRY_START) & (mins < FLATTEN_1545)
            )[0]
            run = 0
            run_side = 0
            for i in watch:
                if np.isnan(vwap[i]):
                    run = 0
                    continue
                side = 1 if close[i] > vwap[i] else (-1 if close[i] < vwap[i] else 0)
                if side == 0 or side != run_side:
                    run_side = side
                    run = 1 if side else 0
                    continue
                run += 1
                day_atr = float(atr_[i])
                if np.isnan(day_atr) or day_atr <= 0:
                    continue
                if run < self.hold_bars:
                    continue
                if abs(close[i] - vwap[i]) < self.min_away_atr * day_atr:
                    continue
                stop_dist = self.stop_atr_mult * day_atr
                entries[i] = side
                stops[i] = close[i] - side * stop_dist
                targets[i] = close[i] + side * stop_dist
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
