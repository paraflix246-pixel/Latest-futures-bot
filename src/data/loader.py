"""
CSV / gzip OHLCV loader for MNQ, NQ, MES.

Resolution order (first hit wins):

  1. data/massive/{SYM}_{tf}.csv.gz   — committed Massive research dump
  2. data/massive/{SYM}_{tf}.csv
  3. data/{SYM}_{tf}.csv              — local / Databento tape

Massive dumps may use `timestamp` instead of `datetime`; both are accepted
and normalized to a UTC DatetimeIndex.

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
MASSIVE_PATH = DATA_PATH / "massive"

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


def _candidate_paths(symbol: str, timeframe: str) -> list[Path]:
    stem = f"{symbol}_{timeframe}"
    return [
        MASSIVE_PATH / f"{stem}.csv.gz",
        MASSIVE_PATH / f"{stem}.csv",
        DATA_PATH / f"{stem}.csv",
    ]


def resolve_ohlcv_path(symbol: str, timeframe: str) -> Path:
    """Return the first existing path for a symbol/timeframe."""
    source_symbol = DERIVED_SYMBOLS.get(symbol, symbol)
    for path in _candidate_paths(source_symbol, timeframe):
        if path.exists():
            return path
    searched = ", ".join(str(p) for p in _candidate_paths(source_symbol, timeframe))
    raise FileNotFoundError(f"No data file for {symbol} ({timeframe}). Looked at: {searched}")


def _normalize_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    if "datetime" not in df.columns and "timestamp" in df.columns:
        df = df.rename(columns={"timestamp": "datetime"})
    if "datetime" not in df.columns:
        raise ValueError("OHLCV file needs a datetime or timestamp column")
    df = df.copy()
    df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    df = df.sort_values("datetime").drop_duplicates(subset="datetime").reset_index(drop=True)
    df = df.set_index("datetime")
    if df.index.tz is None:
        df.index = df.index.tz_localize("UTC")
    else:
        df.index = df.index.tz_convert("UTC")
    missing = [c for c in ("open", "high", "low", "close", "volume") if c not in df.columns]
    if missing:
        raise ValueError(f"OHLCV file missing columns {missing}")
    return df[["open", "high", "low", "close", "volume"]]


def load_ohlcv(symbol: str, timeframe: str) -> pd.DataFrame:
    """Load OHLCV bars for a symbol/timeframe as a DataFrame indexed by datetime."""
    source_symbol = DERIVED_SYMBOLS.get(symbol, symbol)
    try:
        csv_path = resolve_ohlcv_path(source_symbol, timeframe)
        df = pd.read_csv(csv_path)
        return _normalize_ohlcv(df)
    except FileNotFoundError:
        if timeframe in _RESAMPLE_FROM:
            src_tf, rule = _RESAMPLE_FROM[timeframe]
            base = load_ohlcv(symbol, src_tf)
            return resample_ohlcv(base, rule)
        raise


def slice_range(df: pd.DataFrame, start: str | None, end: str | None) -> pd.DataFrame:
    tz = df.index.tz
    if start:
        df = df[df.index >= pd.Timestamp(start, tz=tz)]
    if end:
        df = df[df.index <= pd.Timestamp(end, tz=tz)]
    return df
