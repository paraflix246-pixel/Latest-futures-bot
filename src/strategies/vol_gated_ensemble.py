"""
Sprint-1 ensemble with a prior-session ATR-percentile gate.

Does not retune EMA / Donchian / ADX lengths. The only new claim is that
the existing RTH ensemble should be *silent* in the quietest and most
violent vol regimes (outside [`atr_pct_lo`, `atr_pct_hi`] of a rolling
`lookback` of daily ATR).

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.strategies.base import StrategySignals
from src.strategies.ensemble import EnsembleStrategy
from src.strategies.indicators import atr
from src.strategies.session import session_clock

ATR_PCT_LO = 20.0
ATR_PCT_HI = 80.0
LOOKBACK = 20


class VolGatedEnsembleStrategy:
    name = "vol_gated_ensemble"

    def __init__(
        self,
        atr_pct_lo: float = ATR_PCT_LO,
        atr_pct_hi: float = ATR_PCT_HI,
        lookback: int = LOOKBACK,
        rth_only: bool = True,
        breakout_in_range: bool = False,
        event_trigger: bool = True,
    ):
        self.atr_pct_lo = atr_pct_lo
        self.atr_pct_hi = atr_pct_hi
        self.lookback = lookback
        self._ens = EnsembleStrategy(
            rth_only=rth_only,
            breakout_in_range=breakout_in_range,
            event_trigger=event_trigger,
        )

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        sig = self._ens.generate_signals(df)
        _, dates = session_clock(df.index)
        daily = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
        daily_atr = atr(daily["high"], daily["low"], daily["close"], 14).shift(1)
        pct = daily_atr.rolling(self.lookback, min_periods=max(5, self.lookback // 2)).rank(pct=True) * 100.0
        pct_by_date = {ts.date(): float(v) for ts, v in pct.items()}
        flags = []
        for d in dates:
            p = pct_by_date.get(d, np.nan)
            flags.append((not np.isnan(p)) and self.atr_pct_lo <= p <= self.atr_pct_hi)
        ok = pd.Series(flags, index=df.index)
        entries = sig.entries.where(ok, 0)
        stop = sig.stop_price.where(ok, np.nan)
        target = sig.target_price.where(ok, np.nan)
        return StrategySignals(entries=entries, stop_price=stop, target_price=target)
