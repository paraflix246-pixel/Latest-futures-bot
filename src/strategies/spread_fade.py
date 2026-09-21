"""
Session-spread fade toward VWAP (RTH, day-flat).

Local-hunt near-miss family (`s4_spread_fade2`, MNQ WF t=1.80, failed
robustness — not a PASS). After 10:00, if the cash-session range already
exceeds `spread_atr` × prior-day ATR and the close sits in the outer
quartile of that range, fade toward RTH VWAP.

Stop: stop_atr_mult × ATR. Target = VWAP. Flatten 15:45. One per session.

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

ENTRY_START = 10 * 60
SPREAD_ATR = 0.45
STOP_ATR = 0.30
MAX_HOLD_BARS = 48


class SpreadFadeStrategy:
    name = "spread_fade"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        spread_atr: float = SPREAD_ATR,
        stop_atr_mult: float = STOP_ATR,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.spread_atr = float(spread_atr)
        self.stop_atr_mult = float(stop_atr_mult)
        self.max_hold_bars = int(max_hold_bars)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
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
            day_mask = date_vals == d
            so_far = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < ENTRY_START))[0]
            watch = np.where(day_mask & (mins >= ENTRY_START) & (mins < FLATTEN_1545))[0]
            if len(so_far) == 0 or len(watch) == 0:
                continue
            sess_high = float(high[so_far].max())
            sess_low = float(low[so_far].min())
            for i in watch:
                sess_high = max(sess_high, float(high[i]))
                sess_low = min(sess_low, float(low[i]))
                rng = sess_high - sess_low
                day_atr = float(atr_[i])
                if np.isnan(day_atr) or day_atr <= 0 or rng < self.spread_atr * day_atr:
                    continue
                if np.isnan(vwap[i]):
                    continue
                loc = (close[i] - sess_low) / rng if rng > 0 else 0.5
                if loc >= 0.75:
                    fade = -1
                elif loc <= 0.25:
                    fade = 1
                else:
                    continue
                stop_dist = self.stop_atr_mult * day_atr
                if stop_dist <= 0:
                    break
                entries[i] = fade
                stops[i] = close[i] - fade * stop_dist
                targets[i] = vwap[i]
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
