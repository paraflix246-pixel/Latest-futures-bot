"""
Opening-drive continuation (not an ORB break).

If the first 15 minutes of RTH are a directional drive
(|close-open| ≥ min_atr_frac × prior-day ATR and body ≥ min_body_pct of
range), enter *at the 09:45 ET bar* in that drive direction. Stop is
`stop_atr_mult` × ATR. Target 1R. Flatten 11:00 ET.

This is a clocked continuation of the cash open, not a range break.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.indicators import atr
from src.strategies.session import RTH_CLOSE_MINUTES, RTH_OPEN_MINUTES, session_clock

DRIVE_END = RTH_OPEN_MINUTES + 15
CLOCK_EXIT = 11 * 60
MIN_ATR_FRAC = 0.15
MIN_BODY_PCT = 0.50
STOP_ATR_MULT = 0.35
MAX_HOLD_BARS = 18


class OpenDriveStrategy:
    name = "open_drive"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = CLOCK_EXIT
    session_exit_minutes = CLOCK_EXIT
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        min_atr_frac: float = MIN_ATR_FRAC,
        min_body_pct: float = MIN_BODY_PCT,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.min_atr_frac = min_atr_frac
        self.min_body_pct = min_body_pct
        self.stop_atr_mult = stop_atr_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        open_ = df["open"].to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        prior_atr = _prior_day_atr(df, dates).to_numpy()

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            day_mask = date_vals == d
            drive = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < DRIVE_END))[0]
            entry = np.where(day_mask & (mins == DRIVE_END))[0]
            if len(drive) == 0 or len(entry) == 0:
                continue
            o0 = float(open_[drive[0]])
            c1 = float(close[drive[-1]])
            hi = float(high[drive].max())
            lo = float(low[drive].min())
            rng = hi - lo
            if rng <= 0:
                continue
            body = abs(c1 - o0)
            day_atr = float(prior_atr[entry[0]])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            if body < self.min_atr_frac * day_atr:
                continue
            if (body / rng) < self.min_body_pct:
                continue
            direction = 1 if c1 > o0 else -1
            i = int(entry[0])
            stop_dist = self.stop_atr_mult * day_atr
            if stop_dist <= 0:
                continue
            entries[i] = direction
            stops[i] = close[i] - direction * stop_dist
            targets[i] = close[i] + direction * stop_dist

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )


def _prior_day_atr(df: pd.DataFrame, dates: pd.Series) -> pd.Series:
    daily = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    daily_atr = atr(daily["high"], daily["low"], daily["close"], 14).shift(1)
    atr_by_date = {ts.date(): float(v) for ts, v in daily_atr.items()}
    series = pd.Series([atr_by_date.get(d, np.nan) for d in dates], index=df.index)
    fallback = atr(df["high"], df["low"], df["close"], 14) * np.sqrt(78)
    return series.fillna(fallback)
