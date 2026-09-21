"""
Ensemble: ADX-based regime router rather than naive signal voting (trend and
mean-reversion signals routinely contradict each other, so voting would
cancel out most trades). Per bar:

  - ADX >= 25 (trending)   -> take trend-following signals
  - ADX < 20  (ranging)    -> take mean-reversion signals
  - ADX 20-25 (transition) -> neither trend nor mean-reversion trades
  - breakout signals are event-triggered Donchian breaks; by default they
    do *not* fire in a ranging regime (ADX < 20). The pre-sprint behaviour
    of "breakout always overrides, including inside a range" is available
    via `breakout_in_range=True` for reproduction.

Optional `rth_only=True` zeros entries outside the NYSE cash session
(09:30–16:00 America/New_York). Overnight Globex 5m bars are liquid enough
to exist in the tape but fills/slippage there are worse than the 1-tick
model; RTH-only is a fill-realism / risk overlay, not a claimed edge.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.backtest.session import rth_mask
from src.strategies.base import StrategySignals
from src.strategies.breakout import BreakoutStrategy
from src.strategies.indicators import adx
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.trend_following import TrendFollowingStrategy

ADX_TREND_MIN = 25
ADX_RANGE_MAX = 20
ADX_PERIOD = 14


class EnsembleStrategy:
    name = "ensemble"

    def __init__(
        self,
        adx_trend_min: float = ADX_TREND_MIN,
        adx_range_max: float = ADX_RANGE_MAX,
        rth_only: bool = True,
        breakout_in_range: bool = False,
        event_trigger: bool = True,
    ) -> None:
        self.adx_trend_min = adx_trend_min
        self.adx_range_max = adx_range_max
        self.rth_only = rth_only
        self.breakout_in_range = breakout_in_range
        self.event_trigger = event_trigger
        self._trend = TrendFollowingStrategy()
        self._mean_reversion = MeanReversionStrategy(event_trigger=event_trigger)
        self._breakout = BreakoutStrategy(event_trigger=event_trigger)

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        trend_sig = self._trend.generate_signals(df)
        mr_sig = self._mean_reversion.generate_signals(df)
        bo_sig = self._breakout.generate_signals(df)

        adx_ = adx(df["high"], df["low"], df["close"], ADX_PERIOD)
        trending = adx_ >= self.adx_trend_min
        ranging = adx_ < self.adx_range_max

        entries = pd.Series(0, index=df.index)
        stop_price = pd.Series(np.nan, index=df.index)
        target_price = pd.Series(np.nan, index=df.index)

        entries[trending] = trend_sig.entries[trending]
        stop_price[trending] = trend_sig.stop_price[trending]
        target_price[trending] = trend_sig.target_price[trending]

        entries[ranging] = mr_sig.entries[ranging]
        stop_price[ranging] = mr_sig.stop_price[ranging]
        target_price[ranging] = mr_sig.target_price[ranging]

        bo_fires = bo_sig.entries != 0
        if not self.breakout_in_range:
            bo_fires = bo_fires & ~ranging
        entries[bo_fires] = bo_sig.entries[bo_fires]
        stop_price[bo_fires] = bo_sig.stop_price[bo_fires]
        target_price[bo_fires] = bo_sig.target_price[bo_fires]

        if self.rth_only:
            in_rth = rth_mask(df.index)
            entries = entries.where(in_rth, 0)
            stop_price = stop_price.where(in_rth, np.nan)
            target_price = target_price.where(in_rth, np.nan)

        return StrategySignals(entries=entries, stop_price=stop_price, target_price=target_price)
