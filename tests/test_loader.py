"""Resample 5m bars to 15m / 1h without lookahead."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.data.loader import resample_ohlcv


def test_resample_15m_ohlc_is_bucket_first_max_min_last():
    idx = pd.date_range("2024-01-02 14:30", periods=6, freq="5min", tz="UTC")
    df = pd.DataFrame(
        {
            "open": [10.0, 11, 12, 13, 14, 15],
            "high": [10.5, 12.0, 12.5, 13.5, 16.0, 15.5],
            "low": [9.5, 10.5, 11.0, 12.5, 13.5, 14.5],
            "close": [11.0, 12, 13, 14, 15, 16],
            "volume": [1, 2, 3, 4, 5, 6],
        },
        index=idx,
    )
    out = resample_ohlcv(df, "15min")
    assert len(out) == 2
    first = out.iloc[0]
    assert first["open"] == 10.0
    assert first["high"] == 12.5
    assert first["low"] == 9.5
    assert first["close"] == 13.0
    assert first["volume"] == 6
    second = out.iloc[1]
    assert second["open"] == 13.0
    assert second["high"] == 16.0
    assert second["low"] == 12.5
    assert second["close"] == 16.0
    assert second["volume"] == 15
