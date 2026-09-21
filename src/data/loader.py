"""
CSV OHLCV loader for MNQ, NQ, MES.

NQ has no standalone data file: it tracks the same Nasdaq-100 index at the
same price level as MNQ (both tick_size=0.25), differing only in contract
multiplier/margin/commission. NQ bars are derived by reusing MNQ's price
series unchanged; the $-per-tick difference is applied later by the backtest
engine via the instrument spec, not here.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from config.settings import DATA_DIR, DERIVED_SYMBOLS

DATA_PATH = Path(__file__).resolve().parent.parent.parent / DATA_DIR

# Higher timeframes are resampled from 5m so we do not need separate CSV dumps.
_RESAMPLE_FROM = {
    "15m": ("5m", "15min"),
    "1h": ("5m", "1h"),
}


def resample_ohlcv(df: pd.DataFrame, rule: str) -> pd.DataFrame:
    """Aggregate OHLCV to a coarser bar. Empty buckets (weekends) are dropped."""
    out = df.resample(rule, label="left", closed="left").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    return out.dropna(subset=["open", "high", "low", "close"])


def load_ohlcv(symbol: str, timeframe: str) -> pd.DataFrame:
    """Load OHLCV bars for a symbol/timeframe as a DataFrame indexed by datetime."""
    source_symbol = DERIVED_SYMBOLS.get(symbol, symbol)
    csv_path = DATA_PATH / f"{source_symbol}_{timeframe}.csv"
    if csv_path.exists():
        df = pd.read_csv(csv_path, parse_dates=["datetime"])
        df = df.sort_values("datetime").drop_duplicates(subset="datetime").reset_index(drop=True)
        df = df.set_index("datetime")
        return df[["open", "high", "low", "close", "volume"]]

    if timeframe in _RESAMPLE_FROM:
        src_tf, rule = _RESAMPLE_FROM[timeframe]
        base = load_ohlcv(symbol, src_tf)
        return resample_ohlcv(base, rule)

    raise FileNotFoundError(f"No data file for {symbol} ({timeframe}): {csv_path}")


def slice_range(df: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    tz = df.index.tz
    if start:
        df = df[df.index >= pd.Timestamp(start, tz=tz)]
    if end:
        df = df[df.index <= pd.Timestamp(end, tz=tz)]
    return df
