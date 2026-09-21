"""
Midday compression break (lunch range), RTH only.

Build the 11:30–13:30 ET range. If that range is *compressed* versus
prior-day ATR (`width ≤ lunch_atr_max`), trade the first close beyond it
between 13:30 and 15:00. Stop is the opposite lunch extreme. Flatten 15:45.

This is not an opening-range or last-30m module: the information is the
midday quiet period, not the cash open.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.indicators import atr
from src.strategies.session import RTH_CLOSE_MINUTES, session_clock

LUNCH_START = 11 * 60 + 30
LUNCH_END = 13 * 60 + 30
ENTRY_END = 15 * 60
FLATTEN_MINUTES = 15 * 60 + 45
LUNCH_ATR_MAX = 0.45
VOLUME_MULT = 1.1
TARGET_RANGE_MULT = 1.0
MAX_HOLD_BARS = 24


class LunchRangeBreakStrategy:
    name = "lunch_range_break"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = ENTRY_END
    session_exit_minutes = FLATTEN_MINUTES
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        lunch_atr_max: float = LUNCH_ATR_MAX,
        volume_mult: float = VOLUME_MULT,
        target_range_mult: float = TARGET_RANGE_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.lunch_atr_max = lunch_atr_max
        self.volume_mult = volume_mult
        self.target_range_mult = target_range_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        volume = df["volume"].to_numpy()
        prior_atr = _prior_day_atr(df, dates).to_numpy()

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            day_mask = date_vals == d
            lunch = np.where(day_mask & (mins >= LUNCH_START) & (mins < LUNCH_END))[0]
            if len(lunch) == 0:
                continue
            l_high = float(high[lunch].max())
            l_low = float(low[lunch].min())
            width = l_high - l_low
            if width <= 0:
                continue
            day_atr = float(prior_atr[lunch[-1]])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            if (width / day_atr) > self.lunch_atr_max:
                continue
            avg_vol = float(volume[lunch].mean())
            watch = np.where(day_mask & (mins >= LUNCH_END) & (mins < ENTRY_END))[0]
            for i in watch:
                vol_ok = volume[i] > self.volume_mult * avg_vol
                if close[i] > l_high and vol_ok:
                    entries[i] = 1
                    stops[i] = l_low
                    targets[i] = close[i] + self.target_range_mult * width
                    break
                if close[i] < l_low and vol_ok:
                    entries[i] = -1
                    stops[i] = l_high
                    targets[i] = close[i] - self.target_range_mult * width
                    break

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
