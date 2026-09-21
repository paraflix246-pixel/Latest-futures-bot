"""
RSI(2) dip-buy / spike-fade vs RTH VWAP (RTH, day-flat).

Connors-style 2-period RSI, but the trend filter is session VWAP
instead of a long SMA (this is an intra-cash-session product):

  Long:  RSI(2) ≤ rsi_lo and close ≥ VWAP (buy a dip in an up-session)
  Short: RSI(2) ≥ rsi_hi and close ≤ VWAP

Stop: stop_atr_mult × prior-day ATR. Target 1R. Flatten 15:45.
Skip short sessions. One signal per session. Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.indicators import rsi
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

RSI_LO = 10.0
RSI_HI = 90.0
STOP_ATR_MULT = 0.35
MAX_HOLD_BARS = 24


class Rsi2VwapFadeStrategy:
    name = "rsi2_vwap_fade"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        rsi_lo: float = RSI_LO,
        rsi_hi: float = RSI_HI,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
    ):
        self.rsi_lo = rsi_lo
        self.rsi_hi = rsi_hi
        self.stop_atr_mult = stop_atr_mult
        self.max_hold_bars = max_hold_bars

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        close = df["close"].to_numpy()
        rsi2 = rsi(df["close"], 2).to_numpy()
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
            watch = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES + 30) & (mins < FLATTEN_1545)
            )[0]
            for i in watch:
                if np.isnan(rsi2[i]) or np.isnan(vwap[i]) or np.isnan(atr_[i]) or atr_[i] <= 0:
                    continue
                direction = 0
                if rsi2[i] <= self.rsi_lo and close[i] >= vwap[i]:
                    direction = 1
                elif rsi2[i] >= self.rsi_hi and close[i] <= vwap[i]:
                    direction = -1
                if direction == 0:
                    continue
                stop_dist = self.stop_atr_mult * float(atr_[i])
                entries[i] = direction
                stops[i] = close[i] - direction * stop_dist
                targets[i] = close[i] + direction * stop_dist
                break

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
