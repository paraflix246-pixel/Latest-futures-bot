"""
Volatility squeeze → expansion (RTH only).

Bollinger width at a low percentile *and* Bollinger bands inside Keltner
channels (a TTM-style squeeze). When the squeeze releases — close outside
the Bollinger band with volume — enter in the break direction.

This is not an ATR-shock or Donchian breakout: the trigger is a
compression-then-expansion regime, not a rolling channel or an ATR jump.

  Entry: RTH only, squeeze-on within `release_lookback` bars, close outside
         BB, volume > `volume_mult` × SMA(volume).
  Stop:  opposite Bollinger band (structural, not averaged-down).
  Target: `target_r` × initial risk.
  Clock: engine `max_hold_bars` + flatten at 16:00 ET. No overnight.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.indicators import bollinger_bands, keltner_channels, sma
from src.strategies.session import (
    RTH_CLOSE_MINUTES,
    RTH_ENTRY_CUTOFF_MINUTES,
    in_rth_entry_window,
    session_clock,
)

BB_PERIOD = 20
BB_STD = 2.0
KC_PERIOD = 20
KC_ATR_MULT = 1.5
SQUEEZE_PERCENTILE = 20
SQUEEZE_LOOKBACK = 120
RELEASE_LOOKBACK = 5
VOLUME_MULT = 1.3
VOLUME_PERIOD = 20
TARGET_R = 1.5
MAX_HOLD_BARS = 18  # 90 minutes on 5m


class VolSqueezeExpansionStrategy:
    name = "vol_squeeze_expansion"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = RTH_ENTRY_CUTOFF_MINUTES

    def __init__(
        self,
        squeeze_percentile: float = SQUEEZE_PERCENTILE,
        volume_mult: float = VOLUME_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
        target_r: float = TARGET_R,
        squeeze_lookback: int = SQUEEZE_LOOKBACK,
    ):
        self.squeeze_percentile = squeeze_percentile
        self.volume_mult = volume_mult
        self.max_hold_bars = max_hold_bars
        self.target_r = target_r
        self.squeeze_lookback = squeeze_lookback

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        high, low, close, volume = df["high"], df["low"], df["close"], df["volume"]
        minutes, dates = session_clock(df.index)
        rth = in_rth_entry_window(minutes)

        bb_upper, bb_mid, bb_lower = bollinger_bands(close, BB_PERIOD, BB_STD)
        kc_upper, _, kc_lower = keltner_channels(high, low, close, KC_PERIOD, KC_ATR_MULT)

        bb_width = (bb_upper - bb_lower) / bb_mid.replace(0, np.nan)
        width_pct = bb_width.rolling(self.squeeze_lookback).rank(pct=True) * 100.0
        bb_inside_kc = (bb_upper < kc_upper) & (bb_lower > kc_lower)
        squeeze_on = bb_inside_kc & (width_pct <= self.squeeze_percentile)
        recent_squeeze = squeeze_on.rolling(RELEASE_LOOKBACK, min_periods=1).max().astype(bool)

        vol_ok = volume > self.volume_mult * sma(volume, VOLUME_PERIOD)
        long_break = recent_squeeze & (close > bb_upper) & vol_ok & rth
        short_break = recent_squeeze & (close < bb_lower) & vol_ok & rth

        entries = pd.Series(0, index=df.index)
        stop_price = pd.Series(np.nan, index=df.index)
        target_price = pd.Series(np.nan, index=df.index)

        # One entry per session — first valid release only.
        taken = set()
        for idx in df.index[long_break | short_break]:
            d = dates.loc[idx]
            if d in taken:
                continue
            if long_break.loc[idx]:
                stop = float(bb_lower.loc[idx])
                direction = 1
            else:
                stop = float(bb_upper.loc[idx])
                direction = -1
            px = float(close.loc[idx])
            if np.isnan(stop) or (direction == 1 and px <= stop) or (direction == -1 and px >= stop):
                continue
            risk = abs(px - stop)
            entries.loc[idx] = direction
            stop_price.loc[idx] = stop
            target_price.loc[idx] = px + direction * self.target_r * risk
            taken.add(d)

        return StrategySignals(entries=entries, stop_price=stop_price, target_price=target_price)
