"""Sprint-1 engine still fills next-open; clock exits are additive."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.backtest.engine import run_backtest
from src.strategies.base import StrategySignals


class _HoldForever:
    name = "hold_forever"
    flatten_rth = False
    max_hold_bars = 3

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        entries = pd.Series(0, index=df.index)
        stops = pd.Series(np.nan, index=df.index)
        targets = pd.Series(np.nan, index=df.index)
        entries.iloc[5] = 1
        stops.iloc[5] = float(df["close"].iloc[5]) - 50
        targets.iloc[5] = float(df["close"].iloc[5]) + 500
        return StrategySignals(entries=entries, stop_price=stops, target_price=targets)


def test_max_hold_bars_time_stops_without_changing_fill_model():
    idx = pd.date_range("2026-01-05 14:30", periods=20, freq="5min", tz="UTC")
    px = np.full(20, 20000.0)
    df = pd.DataFrame(
        {"open": px, "high": px + 1, "low": px - 1, "close": px, "volume": 1000},
        index=idx,
    )
    result = run_backtest(
        df,
        _HoldForever(),
        "MNQ",
        "5m",
        50_000,
        0.5,
        fill_model="next_open",
        flatten_at_rth_close=False,
    )
    assert len(result.trades) == 1
    assert result.trades[0].exit_reason == "time_stop"
    # Signal on bar 5, fill next open (bar 6), then 3 subsequent bars -> exit bar 9.
    assert result.trades[0].entry_time == idx[6]


def test_ib_extension_fires_after_first_hour():
    from src.strategies.ib_extension import IbExtensionStrategy
    from src.strategies.session import RTH_OPEN_MINUTES, session_clock

    # 09:00–12:00 ET on a January EST day (UTC-5).
    start = pd.Timestamp("2024-01-03 14:00", tz="UTC")
    idx = pd.date_range(start, periods=36, freq="5min", tz="UTC")
    px = np.full(36, 20000.0)
    df = pd.DataFrame(
        {"open": px, "high": px + 2, "low": px - 2, "close": px, "volume": 1000.0},
        index=idx,
    )
    minutes, _ = session_clock(df.index)
    ib = (minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 60)
    after = minutes >= RTH_OPEN_MINUTES + 60
    df.loc[ib, ["open", "low"]] = 20000.0
    df.loc[ib, ["close", "high"]] = 20020.0
    first = df.index[after][0]
    df.loc[first, ["open", "low"]] = 20020.0
    df.loc[first, ["high", "close"]] = 20080.0
    df.loc[first, "volume"] = 8000.0
    sig = IbExtensionStrategy().generate_signals(df)
    assert sig.entries.loc[first] == 1
    assert sig.stop_price.loc[first] < df.loc[first, "close"]
