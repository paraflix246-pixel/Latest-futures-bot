"""
15-minute trend + 5-minute pullback (RTH only).

Higher-timeframe trend is the last *completed* 15m EMA(8/21) state —
shifted so the in-progress 15m bar cannot leak. On 5m, wait for a
pullback that touches the 15m EMA(8) (mapped onto 5m) or RTH VWAP,
then enter when the 5m close resumes in the 15m trend direction.

Stop: `stop_atr_mult` × prior-day ATR. Target 1R. Flatten 15:45.
Skip short sessions. Same params on MNQ and MES.

Paper / backtest only.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.data.loader import resample_ohlcv
from src.strategies.base import StrategySignals
from src.strategies.indicators import ema
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    prior_day_atr,
    rth_session_vwap,
    session_clock,
    short_session_dates,
)

FAST = 8
SLOW = 21
STOP_ATR_MULT = 0.40
MAX_HOLD_BARS = 48


class Trend15Pullback5Strategy:
    name = "trend15_pullback5"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        fast: int = FAST,
        slow: int = SLOW,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
        breakeven_r_mult: float | None = None,
    ):
        self.fast = fast
        self.slow = slow
        self.stop_atr_mult = stop_atr_mult
        self.max_hold_bars = max_hold_bars
        if breakeven_r_mult is not None:
            self.breakeven_r_mult = breakeven_r_mult

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        df15 = resample_ohlcv(df, "15min")
        fast15 = ema(df15["close"], self.fast)
        slow15 = ema(df15["close"], self.slow)
        # Last completed 15m bar only (no lookahead into the live bucket).
        trend15 = pd.Series(0, index=df15.index)
        trend15[(fast15 > slow15) & (df15["close"] > fast15)] = 1
        trend15[(fast15 < slow15) & (df15["close"] < fast15)] = -1
        trend15 = trend15.shift(1)
        ema15 = fast15.shift(1)
        trend5 = trend15.reindex(df.index, method="ffill").fillna(0)
        ema5 = ema15.reindex(df.index, method="ffill")
        vwap = rth_session_vwap(df["high"], df["low"], df["close"], df["volume"])
        atr_ = prior_day_atr(df, dates)
        holidays = short_session_dates(df)

        entries = pd.Series(0, index=df.index)
        stops = pd.Series(np.nan, index=df.index)
        targets = pd.Series(np.nan, index=df.index)

        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        high = df["high"].to_numpy()
        low = df["low"].to_numpy()
        close = df["close"].to_numpy()
        trend = trend5.to_numpy()
        ema_px = ema5.to_numpy()
        vwap_px = vwap.to_numpy()
        atr_px = atr_.to_numpy()

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            day_mask = date_vals == d
            watch = np.where(
                day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < FLATTEN_1545) & (trend != 0)
            )[0]
            pulled = False
            direction = 0
            for i in watch:
                direction = int(trend[i])
                if direction == 0:
                    continue
                level = ema_px[i]
                if np.isnan(level) and not np.isnan(vwap_px[i]):
                    level = vwap_px[i]
                if np.isnan(level):
                    continue
                if low[i] <= level <= high[i]:
                    pulled = True
                if not pulled:
                    continue
                resume = (direction == 1 and close[i] > level) or (direction == -1 and close[i] < level)
                if not resume:
                    continue
                day_atr = float(atr_px[i])
                if np.isnan(day_atr) or day_atr <= 0:
                    break
                stop_dist = self.stop_atr_mult * day_atr
                entries.iloc[i] = direction
                stops.iloc[i] = close[i] - direction * stop_dist
                targets.iloc[i] = close[i] + direction * stop_dist
                break

        return StrategySignals(entries=entries, stop_price=stops, target_price=targets)
