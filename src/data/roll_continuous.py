"""Front-month roll of per-contract OHLCV into a continuous series.

Picks a daily front month (highest prior-day volume among contracts still
at least `min_days_to_expiry` from last trade), then stitches those
sessions. Prices are backward ratio-adjusted so the most recent segment
matches the raw front-month print.

Paper / research only — this is a back-adjusted continuous, not a traded
instrument you can buy.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd


@dataclass
class RollEvent:
    timestamp: pd.Timestamp
    from_ticker: str
    to_ticker: str
    from_close: float
    to_close: float
    ratio: float


def _as_utc_index(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    if "datetime" in out.columns:
        out["datetime"] = pd.to_datetime(out["datetime"], utc=True)
        out = out.set_index("datetime")
    if out.index.tz is None:
        out.index = out.index.tz_localize("UTC")
    else:
        out.index = out.index.tz_convert("UTC")
    return out.sort_index()


def pick_front_month(
    frames: Dict[str, pd.DataFrame],
    contracts: Iterable[Dict],
    min_days_to_expiry: int = 5,
) -> Tuple[pd.DataFrame, List[RollEvent]]:
    """Build an unadjusted front-month tape and the list of roll events."""
    meta: Dict[str, pd.Timestamp] = {}
    for c in contracts:
        ticker = c.get("ticker")
        if not ticker or ticker not in frames:
            continue
        last = pd.to_datetime(c.get("last_trade_date") or c.get("settlement_date"))
        if pd.isna(last):
            continue
        meta[ticker] = last.tz_localize(None)

    clean: Dict[str, pd.DataFrame] = {}
    for ticker, df in frames.items():
        if ticker not in meta:
            continue
        bar = _as_utc_index(df)
        need = ["open", "high", "low", "close", "volume"]
        missing = [c for c in need if c not in bar.columns]
        if missing:
            raise ValueError(f"{ticker} missing columns {missing}")
        clean[ticker] = bar[need]

    if not clean:
        raise ValueError("No overlapping contracts to roll")

    daily_vol = {t: g["volume"].resample("1D").sum() for t, g in clean.items()}
    all_days = None
    for series in daily_vol.values():
        all_days = series.index if all_days is None else all_days.union(series.index)
    assert all_days is not None
    all_days = all_days.sort_values()

    daily_front: List[Tuple[pd.Timestamp, str]] = []
    prev_ticker = None
    rolls: List[RollEvent] = []
    for day in all_days:
        day_naive = day.tz_localize(None) if day.tzinfo else day
        candidates = []
        for ticker, last in meta.items():
            days_left = (last - day_naive).days
            if days_left < min_days_to_expiry:
                continue
            vol_series = daily_vol[ticker]
            vol = float(vol_series.asof(day)) if len(vol_series) else 0.0
            if np.isnan(vol):
                vol = 0.0
            if vol <= 0 and day not in vol_series.index:
                continue
            candidates.append((vol, days_left, ticker))
        if not candidates:
            continue
        candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        ticker = candidates[0][2]
        if prev_ticker is not None and ticker != prev_ticker:
            from_close = float(clean[prev_ticker]["close"].asof(day))
            to_close = float(clean[ticker]["close"].asof(day))
            if from_close and from_close > 0 and to_close and to_close > 0:
                ratio = to_close / from_close
            else:
                ratio = 1.0
            rolls.append(
                RollEvent(
                    timestamp=pd.Timestamp(day),
                    from_ticker=prev_ticker,
                    to_ticker=ticker,
                    from_close=from_close,
                    to_close=to_close,
                    ratio=float(ratio) if np.isfinite(ratio) else 1.0,
                )
            )
        daily_front.append((day, ticker))
        prev_ticker = ticker

    chunks = []
    for day, ticker in daily_front:
        bar = clean[ticker]
        day_start = pd.Timestamp(day)
        day_end = day_start + pd.Timedelta(days=1)
        sl = bar[(bar.index >= day_start) & (bar.index < day_end)].copy()
        if sl.empty:
            continue
        sl["ticker"] = ticker
        chunks.append(sl)
    if not chunks:
        raise ValueError("Front-month stitch produced no bars")
    raw = pd.concat(chunks).sort_index()
    raw = raw[~raw.index.duplicated(keep="last")]
    return raw, rolls


def backward_ratio_adjust(raw: pd.DataFrame, rolls: List[RollEvent]) -> pd.DataFrame:
    """Scale older segments so the latest prices stay at raw front-month levels."""
    if raw.empty:
        return raw.copy()
    out = raw.copy()
    factor = pd.Series(1.0, index=out.index)
    scale = 1.0
    for event in sorted(rolls, key=lambda e: e.timestamp, reverse=True):
        ratio = event.ratio if event.ratio and np.isfinite(event.ratio) and event.ratio > 0 else 1.0
        scale *= 1.0 / ratio
        factor.loc[factor.index < event.timestamp] = scale
    for col in ("open", "high", "low", "close"):
        out[col] = out[col] * factor
    return out


def to_loader_csv(df: pd.DataFrame) -> pd.DataFrame:
    """Match data/{SYM}_{tf}.csv schema used by src.data.loader."""
    out = df.reset_index()
    if "datetime" not in out.columns:
        out = out.rename(columns={out.columns[0]: "datetime"})
    keep = ["datetime", "open", "high", "low", "close", "volume"]
    return out[keep].sort_values("datetime").drop_duplicates("datetime", keep="last")
