"""Sprint-1 engine/strategy fixes: event triggers, fills, risk caps, RTH."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.session import rth_mask
from src.risk.position_sizing import contracts_for_risk
from src.strategies.base import StrategySignals
from src.strategies.breakout import BreakoutStrategy
from src.strategies.ensemble import EnsembleStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
from config.instruments import get_spec


def _make_df(closes, volumes=None, high_pad=1.0, low_pad=1.0, freq="5min", start="2026-01-01"):
    idx = pd.date_range(start, periods=len(closes), freq=freq, tz="UTC")
    closes = np.array(closes, dtype=float)
    if volumes is None:
        volumes = np.full(len(closes), 1000)
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes + high_pad,
            "low": closes - low_pad,
            "close": closes,
            "volume": volumes,
        },
        index=idx,
    )


def test_breakout_event_trigger_fires_once_not_every_bar_beyond_channel():
    closes = [20000 + (i % 3) for i in range(25)] + [20100, 20110, 20120]
    volumes = [1000] * 25 + [5000, 5000, 5000]
    df = _make_df(closes, volumes=volumes)
    edge = BreakoutStrategy(event_trigger=True).generate_signals(df)
    level = BreakoutStrategy(event_trigger=False).generate_signals(df)
    assert edge.entries.iloc[-3] == 1
    assert edge.entries.iloc[-2] == 0
    assert edge.entries.iloc[-1] == 0
    assert (level.entries.iloc[-3:] == 1).all()


def test_mean_reversion_event_trigger_does_not_repeat_while_stretched():
    closes = [20000] * 150 + [19950, 19940, 19930] + [20000] * 5
    df = _make_df(closes)
    edge = MeanReversionStrategy(event_trigger=True).generate_signals(df)
    level = MeanReversionStrategy(event_trigger=False).generate_signals(df)
    assert (edge.entries != 0).sum() <= (level.entries != 0).sum()
    # Once the fade condition is on, extra bars in the hole are not new trades.
    fired = np.where((edge.entries != 0).to_numpy())[0]
    assert len(fired) >= 1
    # Consecutive stretched bars must not all be new entries.
    assert len(fired) < (level.entries != 0).sum() or (level.entries != 0).sum() <= 1


def test_no_same_bar_reentry():
    closes = [20000] * 20 + [20000 + (i % 2) * 40 for i in range(30)]
    df = _make_df(closes, high_pad=50, low_pad=50)

    class AlwaysLong:
        name = "always_long"

        def generate_signals(self, df):
            entries = pd.Series(1, index=df.index)
            stop = df["close"] - 5
            target = df["close"] + 5
            return StrategySignals(entries=entries, stop_price=stop, target_price=target)

    result = run_backtest(
        df, AlwaysLong(), "MNQ", "5m", 50_000, 0.5,
        fill_model="signal_close",
        apply_exit_slippage=False,
        gap_aware_stops=False,
        trail_update="same_bar",
        cooldown_bars=0,
        allow_same_bar_reentry=False,
        daily_loss_halt_pct=None,
        flatten_at_rth_close=False,
        max_contracts=10,
    )
    for i in range(len(result.trades) - 1):
        assert result.trades[i + 1].entry_time != result.trades[i].exit_time


def test_gap_through_stop_fills_at_open_not_stop():
    # Flat, enter long, next bar gaps through the stop.
    closes = [20000] * 30 + [19900]
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="5min", tz="UTC")
    closes = np.array(closes, dtype=float)
    opens = closes.copy()
    opens[-1] = 19880  # gap open well below stop
    df = pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(opens, closes) + 1,
            "low": np.minimum(opens, closes) - 1,
            "close": closes,
            "volume": np.full(len(closes), 1000),
        },
        index=idx,
    )

    class OneShot:
        name = "one"
        def generate_signals(self, df):
            entries = pd.Series(0, index=df.index)
            stop = pd.Series(np.nan, index=df.index)
            target = pd.Series(np.nan, index=df.index)
            entries.iloc[28] = 1
            stop.iloc[28] = 19950
            target.iloc[28] = 21000
            return StrategySignals(entries=entries, stop_price=stop, target_price=target)

    result = run_backtest(
        df, OneShot(), "MNQ", "5m", 50_000, 0.5,
        fill_model="next_open",
        apply_exit_slippage=False,
        gap_aware_stops=True,
        trail_update="next_bar",
        cooldown_bars=0,
        allow_same_bar_reentry=False,
        daily_loss_halt_pct=None,
        flatten_at_rth_close=False,
        max_contracts=10,
        slippage_ticks=0,
    )
    assert len(result.trades) == 1
    # Filled at bar 29 open (=20000), then bar 30 gaps to 19880 through 19950 stop.
    assert result.trades[0].exit_price == 19880


def test_max_contracts_caps_tight_stop_size():
    spec = get_spec("MNQ")
    # 2-tick stop = $1 risk/contract; 0.5% of 50k = $250 -> 250 uncapped.
    n = contracts_for_risk(50_000, 0.5, 20000, 19999.50, spec, max_contracts=10)
    assert n == 10
    n_uncapped = contracts_for_risk(50_000, 0.5, 20000, 19999.50, spec, max_contracts=None)
    assert n_uncapped > 10


def test_ensemble_rth_only_zeros_overnight_entries():
    idx = pd.date_range("2024-01-02 00:00", periods=288, freq="5min", tz="UTC")
    close = pd.Series(20000 + np.linspace(0, 50, len(idx)), index=idx)
    df = pd.DataFrame(
        {
            "open": close,
            "high": close + 2,
            "low": close - 2,
            "close": close,
            "volume": np.full(len(idx), 2000.0),
        },
        index=idx,
    )
    sig = EnsembleStrategy(rth_only=True, breakout_in_range=False).generate_signals(df)
    mask = rth_mask(df.index)
    overnight_fires = (sig.entries != 0) & ~mask
    assert overnight_fires.sum() == 0


def test_next_open_fill_uses_following_bar_open():
    closes = [20000] * 30 + [20050 + i * 5 for i in range(20)]
    idx = pd.date_range("2026-01-01", periods=len(closes), freq="5min", tz="UTC")
    closes = np.array(closes, dtype=float)
    opens = closes.copy()
    opens[30] = 20010  # fill bar open distinct from signal close 20000
    df = pd.DataFrame(
        {
            "open": opens,
            "high": np.maximum(opens, closes) + 1,
            "low": np.minimum(opens, closes) - 1,
            "close": closes,
            "volume": np.full(len(closes), 1000),
        },
        index=idx,
    )

    class OneShot:
        name = "one"
        def generate_signals(self, df):
            entries = pd.Series(0, index=df.index)
            stop = pd.Series(np.nan, index=df.index)
            target = pd.Series(np.nan, index=df.index)
            entries.iloc[29] = 1
            stop.iloc[29] = 19950
            target.iloc[29] = 20100
            return StrategySignals(entries=entries, stop_price=stop, target_price=target)

    result = run_backtest(
        df, OneShot(), "MNQ", "5m", 50_000, 0.5,
        fill_model="next_open",
        apply_exit_slippage=False,
        gap_aware_stops=True,
        trail_update="next_bar",
        cooldown_bars=0,
        allow_same_bar_reentry=False,
        daily_loss_halt_pct=None,
        flatten_at_rth_close=False,
        slippage_ticks=0,
        max_contracts=10,
    )
    assert len(result.trades) == 1
    assert result.trades[0].entry_price == 20010
    assert result.trades[0].entry_time == df.index[30]
