"""
Prior-day midpoint reclaim (RTH, day-flat).

After 10:00, if price has been ≥ min_away_atr × ATR away from the prior
RTH midpoint and later closes back through that midpoint, enter in the
reclaim direction. Stop: stop_atr_mult × ATR. Target 1R. Flatten 15:45.
One per session.

Paper / backtest only. No live trading.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    prior_day_atr,
    prior_rth_hlc_by_date,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

ENTRY_START = 10 * 60
MIN_AWAY = 0.15
STOP_ATR = 0.30
MAX_HOLD_BARS = 48


class PriorMidReclaimStrategy:
    name = "prior_mid_reclaim"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        min_away_atr: float = MIN_AWAY,
        stop_atr_mult: float = STOP_ATR,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
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
        prior = prior_rth_hlc_by_date(df)
        holidays = short_session_dates(df)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            prev = prior.get(d)
            if not prev:
                continue
            mid = 0.5 * (prev["high"] + prev["low"])
            day_mask = date_vals == d
            watch = np.where(day_mask & (mins >= ENTRY_START) & (mins < FLATTEN_1545))[0]
            if len(watch) == 0:
                continue
            seen = 0
            for i in watch:
                day_atr = float(atr_[i])
                if np.isnan(day_atr) or day_atr <= 0:
                    continue
                dist = close[i] - mid
                if seen == 0:
                    if dist >= self.min_away_atr * day_atr:
                        seen = 1
                    elif dist <= -self.min_away_atr * day_atr:
                        seen = -1
                    continue
                reclaimed = (seen == 1 and close[i] < mid) or (seen == -1 and close[i] > mid)
                if not reclaimed:
                    continue
                fade = -seen
                if not np.isnan(vwap[i]):
                    if fade == 1 and close[i] < vwap[i]:
                        continue
                    if fade == -1 and close[i] > vwap[i]:
                        continue
                stop_dist = self.stop_atr_mult * day_atr
                if stop_dist <= 0:
                    break
                entries[i] = fade
                stops[i] = close[i] - fade * stop_dist
                targets[i] = close[i] + fade * stop_dist
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
