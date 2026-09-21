"""
Failed previous-day high / low (RTH, day-flat).

First RTH test of yesterday's cash high or low that wicks through and
closes back inside is faded:

  - high > PDH and close < PDH → short
  - low < PDL and close > PDL → long

Stop: beyond the wick by stop_atr_mult × prior-day ATR. Target 1R.
Flatten 15:45. Skip short sessions and overnight-expansion days
(overnight range > 1.5 × 20-day ADR). One signal per session.

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
    adr20_by_date,
    overnight_range_by_date,
    prior_day_atr,
    prior_rth_hlc_by_date,
    session_clock,
    short_session_dates,
)

ENTRY_START = RTH_OPEN_MINUTES + 15
ON_ADR_MULT = 1.50
STOP_ATR_MULT = 0.20
MAX_HOLD_BARS = 60


class PdhPdlFailStrategy:
    name = "pdh_pdl_fail"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        stop_atr_mult: float = STOP_ATR_MULT,
        on_adr_mult: float = ON_ADR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.stop_atr_mult = stop_atr_mult
        self.on_adr_mult = on_adr_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        prior = prior_rth_hlc_by_date(df)
        on_range = overnight_range_by_date(df)
        adr = adr20_by_date(df)
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            prev = prior.get(d)
            if prev is None:
                continue
            on_r = on_range.get(d)
            day_adr = adr.get(d)
            if on_r is not None and day_adr and day_adr > 0 and on_r > self.on_adr_mult * day_adr:
                continue
            day_mask = date_vals == d
            watch = np.where(day_mask & (mins >= ENTRY_START) & (mins < FLATTEN_1545))[0]
            pdh, pdl = prev["high"], prev["low"]
            for i in watch:
                day_atr = float(atr_[i])
                if np.isnan(day_atr) or day_atr <= 0:
                    continue
                pad = self.stop_atr_mult * day_atr
                if high[i] > pdh and close[i] < pdh:
                    stop = max(high[i], pdh) + pad
                    risk = stop - close[i]
                    if risk <= 0:
                        continue
                    entries[i] = -1
                    stops[i] = stop
                    targets[i] = close[i] - risk
                    break
                if low[i] < pdl and close[i] > pdl:
                    stop = min(low[i], pdl) - pad
                    risk = close[i] - stop
                    if risk <= 0:
                        continue
                    entries[i] = 1
                    stops[i] = stop
                    targets[i] = close[i] + risk
                    break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
