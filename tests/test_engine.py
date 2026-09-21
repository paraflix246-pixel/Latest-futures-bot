"""Sanity checks for the backtest engine on small synthetic OHLCV series."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import pytest

from src.backtest.engine import run_backtest
from src.strategies.base import StrategySignals


class _OneShotLongStrategy:
    """Fires a single long entry on bar `entry_idx` with a fixed stop/target."""

    name = "one_shot_long"

    def __init__(self, entry_idx: int, stop: float, target: float):
        self.entry_idx = entry_idx
        self.stop = stop
        self.target = target

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        entries = pd.Series(0, index=df.index)
        stop_price = pd.Series(np.nan, index=df.index)
        target_price = pd.Series(np.nan, index=df.index)
        entries.iloc[self.entry_idx] = 1
        stop_price.iloc[self.entry_idx] = self.stop
        target_price.iloc[self.entry_idx] = self.target
        return StrategySignals(entries=entries, stop_price=stop_price, target_price=target_price)


def _make_df(closes):
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="5min")
    closes = np.array(closes, dtype=float)
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes + 1.0,
            "low": closes - 1.0,
            "close": closes,
            "volume": np.full(len(closes), 1000),
        },
        index=idx,
    )


def test_long_trade_hits_target():
    # Flat then a clean rally so the target (well above entry) gets hit.
    closes = [20000] * 30 + [20050 + i * 5 for i in range(20)]
    df = _make_df(closes)
    strategy = _OneShotLongStrategy(entry_idx=29, stop=19950, target=20100)

    result = run_backtest(
        df=df, strategy=strategy, symbol="MNQ", timeframe="5m",
        account_size=50_000, risk_pct=0.5,
    )

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.direction == 1
    assert trade.exit_reason == "target"
    assert trade.pnl > 0
    assert trade.contracts > 0


def test_long_trade_hits_stop():
    closes = [20000] * 30 + [19980 - i * 5 for i in range(20)]
    df = _make_df(closes)
    strategy = _OneShotLongStrategy(entry_idx=29, stop=19900, target=20200)

    result = run_backtest(
        df=df, strategy=strategy, symbol="MNQ", timeframe="5m",
        account_size=50_000, risk_pct=0.5,
    )

    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason == "stop"
    assert trade.pnl < 0


def test_no_signals_means_no_trades():
    closes = [20000 + (i % 5) for i in range(50)]
    df = _make_df(closes)

    class NoOpStrategy:
        name = "noop"

        def generate_signals(self, df):
            zeros = pd.Series(0, index=df.index)
            nans = pd.Series(np.nan, index=df.index)
            return StrategySignals(entries=zeros, stop_price=nans, target_price=nans)

    result = run_backtest(
        df=df, strategy=NoOpStrategy(), symbol="MES", timeframe="5m",
        account_size=50_000, risk_pct=0.5,
    )
    assert len(result.trades) == 0
    assert result.equity_curve.iloc[-1] == 50_000


def test_oversized_risk_skips_trade():
    # Stop is enormous relative to a tiny risk budget -> 0 contracts -> no trade opened.
    closes = [20000] * 30 + [20050 + i * 5 for i in range(20)]
    df = _make_df(closes)
    strategy = _OneShotLongStrategy(entry_idx=29, stop=10000, target=25000)

    result = run_backtest(
        df=df, strategy=strategy, symbol="MNQ", timeframe="5m",
        account_size=100, risk_pct=0.1,
    )
    assert len(result.trades) == 0


class _TimedLongStrategy:
    """Single long with optional clock / RTH flatten attrs."""

    name = "timed_long"

    def __init__(self, entry_idx: int, stop: float, target: float, max_hold_bars=None, flatten_rth=False):
        self.entry_idx = entry_idx
        self.stop = stop
        self.target = target
        self.max_hold_bars = max_hold_bars
        self.flatten_rth = flatten_rth

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        entries = pd.Series(0, index=df.index)
        stop_price = pd.Series(np.nan, index=df.index)
        target_price = pd.Series(np.nan, index=df.index)
        entries.iloc[self.entry_idx] = 1
        stop_price.iloc[self.entry_idx] = self.stop
        target_price.iloc[self.entry_idx] = self.target
        return StrategySignals(entries=entries, stop_price=stop_price, target_price=target_price)


def test_max_hold_bars_exits_at_close():
    # Wide stop/target so the clock is the only exit. Entry on bar 5; after
    # 3 subsequent bars the time-stop must flatten at that close.
    idx = pd.date_range("2024-01-03 15:00", periods=12, freq="5min", tz="UTC")
    close = np.full(12, 20000.0)
    df = pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1000},
        index=idx,
    )
    strategy = _TimedLongStrategy(entry_idx=2, stop=19900, target=22000, max_hold_bars=3)
    result = run_backtest(df=df, strategy=strategy, symbol="MNQ", timeframe="5m",
                          account_size=50_000, risk_pct=0.5)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason == "time_stop"
    assert trade.exit_time == idx[2 + 3]


def test_rth_flatten_closes_before_overnight():
    # 15:00–16:30 ET on 2024-01-03 (EST = UTC-5). Enter 15:00, never hit
    # stop/target; engine must flatten at the 16:00 ET bar, not hold into 16:30.
    idx = pd.date_range("2024-01-03 20:00", periods=20, freq="5min", tz="UTC")
    close = np.full(20, 20000.0)
    df = pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1000},
        index=idx,
    )
    strategy = _TimedLongStrategy(entry_idx=0, stop=19900, target=22000, flatten_rth=True)
    result = run_backtest(df=df, strategy=strategy, symbol="MNQ", timeframe="5m",
                          account_size=50_000, risk_pct=0.5)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason == "rth_flatten"
    # 16:00 ET = 21:00 UTC
    assert trade.exit_time == pd.Timestamp("2024-01-03 21:00", tz="UTC")
    assert trade.exit_time.tz_convert("America/New_York").hour == 16


def test_rth_flatten_blocks_entries_after_cutoff():
    # Signal at 15:45 ET must not open — cutoff is 15:30 when flatten_rth is on.
    idx = pd.date_range("2024-01-03 20:40", periods=8, freq="5min", tz="UTC")  # 15:40 ET
    close = np.full(8, 20000.0)
    df = pd.DataFrame(
        {"open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1000},
        index=idx,
    )
    strategy = _TimedLongStrategy(entry_idx=1, stop=19900, target=22000, flatten_rth=True)
    result = run_backtest(df=df, strategy=strategy, symbol="MNQ", timeframe="5m",
                          account_size=50_000, risk_pct=0.5)
    assert result.trades == []
