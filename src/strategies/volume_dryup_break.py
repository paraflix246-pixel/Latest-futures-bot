"""
Intraday dry-up then expansion break (RTH, day-flat).

After 10:30, if the last `lookback` 5m bars are a tight range
(range < nr_frac × prior-day ATR) *and* their mean volume is below
`vol_dry` × first-hour mean volume, take the first later bar that
expands (volume > vol_exp × lookback mean) and closes beyond that
range. Stop: opposite side of the dry-up range. Target 1R.
Flatten 15:45. One signal per session.

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
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

ENTRY_START = 10 * 60 + 30
LOOKBACK = 8
NR_FRAC = 0.50
VOL_DRY = 0.70
VOL_EXP = 1.50
MAX_HOLD_BARS = 36


class VolumeDryupBreakStrategy:
    name = "volume_dryup_break"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        lookback: int = LOOKBACK,
        nr_frac: float = NR_FRAC,
        vol_dry: float = VOL_DRY,
        vol_exp: float = VOL_EXP,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.lookback = int(lookback)
        self.nr_frac = float(nr_frac)
        self.vol_dry = float(vol_dry)
        self.vol_exp = float(vol_exp)
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
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            first_hour = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + 60)
            )[0]
            watch = np.where(day_mask & (mins >= ENTRY_START) & (mins < FLATTEN_1545))[0]
            if len(first_hour) == 0 or len(watch) < self.lookback + 1:
                continue
            hour_vol = float(volume[first_hour].mean())
            if hour_vol <= 0:
                continue
            issued = False
            for k, i in enumerate(watch):
                if issued:
                    break
                if k < self.lookback:
                    continue
                window = watch[k - self.lookback : k]
                box_hi = float(high[window].max())
                box_lo = float(low[window].min())
                box_rng = box_hi - box_lo
                box_vol = float(volume[window].mean())
                day_atr = float(atr_[i])
                if np.isnan(day_atr) or day_atr <= 0 or box_rng <= 0:
                    continue
                if box_rng >= self.nr_frac * day_atr:
                    continue
                if box_vol >= self.vol_dry * hour_vol:
                    continue
                if volume[i] < self.vol_exp * box_vol:
                    continue
                direction = 0
                if close[i] > box_hi:
                    direction = 1
                elif close[i] < box_lo:
                    direction = -1
                if direction == 0:
                    continue
                if not np.isnan(vwap[i]):
                    if direction == 1 and close[i] < vwap[i]:
                        continue
                    if direction == -1 and close[i] > vwap[i]:
                        continue
                stop = box_lo if direction == 1 else box_hi
                risk = abs(close[i] - stop)
                if risk <= 0:
                    continue
                entries[i] = direction
                stops[i] = stop
                targets[i] = close[i] + direction * risk
                issued = True

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
