"""
Cross-symbol open drive: the *other* index's first 15m sets the bias.

MNQ uses MES 09:30–09:45 close vs open; MES uses MNQ. Enter at 09:45 only
if this symbol's first 15m agrees. Stop ATR, target 1R, flatten 15:45.

This is not a candlestick pattern on the traded chart — it is a lead/lag
between the two micros. Paper / backtest only.
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
    session_clock,
    short_session_dates,
)

DRIVE_END = RTH_OPEN_MINUTES + 15
STOP_ATR_MULT = 0.30
MAX_HOLD_BARS = 72
_BIAS_CACHE: dict = {}


def _infer_tf(df: pd.DataFrame) -> str:
    if len(df) < 2:
        return "5m"
    dt = float((df.index[1] - df.index[0]).total_seconds())
    return "1m" if dt <= 90 else "5m"


def _open15_bias_by_date(symbol: str, timeframe: str) -> dict:
    key = (symbol, timeframe)
    if key in _BIAS_CACHE:
        return _BIAS_CACHE[key]
    from src.data.loader import load_ohlcv

    odf = load_ohlcv(symbol, timeframe)
    minutes, dates = session_clock(odf.index)
    mins = minutes.to_numpy()
    date_vals = dates.to_numpy()
    open_ = odf["open"].to_numpy()
    close = odf["close"].to_numpy()
    out = {}
    for d in pd.unique(date_vals):
        drive = np.where((date_vals == d) & (mins >= RTH_OPEN_MINUTES) & (mins < DRIVE_END))[0]
        if len(drive) == 0:
            continue
        o0, c1 = float(open_[drive[0]]), float(close[drive[-1]])
        if c1 > o0:
            out[d] = 1
        elif c1 < o0:
            out[d] = -1
    _BIAS_CACHE[key] = out
    return out


class CrossLeadOpen15Strategy:
    name = "cross_lead_open15"
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = MAX_HOLD_BARS

    def __init__(
        self,
        stop_atr_mult: float = STOP_ATR_MULT,
        max_hold_bars: int = MAX_HOLD_BARS,
        lead_symbol: str | None = None,
    ):
        self.stop_atr_mult = float(stop_atr_mult)
        self.max_hold_bars = int(max_hold_bars)
        self.lead_symbol = lead_symbol

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        open_ = df["open"].to_numpy()
        close = df["close"].to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        holidays = short_session_dates(df)
        tf = _infer_tf(df)
        # Infer traded symbol from typical price level (MNQ ~20k, MES ~5k).
        med = float(np.nanmedian(close))
        traded = "MNQ" if med > 10000 else "MES"
        lead = self.lead_symbol or ("MES" if traded == "MNQ" else "MNQ")
        lead_bias = _open15_bias_by_date(lead, tf)

        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)

        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            bias = lead_bias.get(d, 0)
            if bias == 0:
                continue
            day_mask = date_vals == d
            drive = np.where(day_mask & (mins >= RTH_OPEN_MINUTES) & (mins < DRIVE_END))[0]
            entry = np.where(day_mask & (mins == DRIVE_END))[0]
            if len(drive) == 0 or len(entry) == 0:
                continue
            o0, c1 = float(open_[drive[0]]), float(close[drive[-1]])
            local = 1 if c1 > o0 else (-1 if c1 < o0 else 0)
            if local != bias:
                continue
            i = int(entry[0])
            day_atr = float(atr_[i])
            if np.isnan(day_atr) or day_atr <= 0:
                continue
            stop_dist = self.stop_atr_mult * day_atr
            entries[i] = bias
            stops[i] = close[i] - bias * stop_dist
            targets[i] = close[i] + bias * stop_dist

        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )
