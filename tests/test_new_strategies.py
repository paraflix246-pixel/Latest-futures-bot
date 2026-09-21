"""Signal-shape and constructed-pattern tests for the RTH session strategies."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.backtest.engine import run_backtest
from src.strategies.impulse_clock import ImpulseClockStrategy
from src.strategies.orb_break_fade import OrbBreakFadeStrategy
from src.strategies.session import RTH_OPEN_MINUTES, session_clock
from src.strategies.vol_squeeze_expansion import VolSqueezeExpansionStrategy


def _rth_day(date="2024-01-03", start_et_minutes=9 * 60, n_bars=90, price=20000.0, noise=0.4):
    """5m bars covering a cash session. January 2024 is EST (UTC-5)."""
    start_utc_hour = (start_et_minutes // 60) + 5
    start_utc_min = start_et_minutes % 60
    start = pd.Timestamp(f"{date} {start_utc_hour:02d}:{start_utc_min:02d}", tz="UTC")
    idx = pd.date_range(start, periods=n_bars, freq="5min", tz="UTC")
    closes = np.full(n_bars, float(price))
    if noise:
        rng = np.random.default_rng(0)
        closes = closes + rng.normal(0, noise, size=n_bars)
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes + 1.0,
            "low": closes - 1.0,
            "close": closes,
            "volume": np.full(n_bars, 1000.0),
        },
        index=idx,
    )


def test_orb_break_fade_enters_volume_confirmed_break():
    df = _rth_day(n_bars=40, noise=0.0)
    minutes, _ = session_clock(df.index)
    or_mask = (minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 15)
    after = minutes >= RTH_OPEN_MINUTES + 15
    # Opening range 20000–20020.
    df.loc[or_mask, ["open", "low"]] = 20000.0
    df.loc[or_mask, ["close", "high"]] = 20020.0
    first_after = df.index[after][0]
    df.loc[first_after, ["open", "low"]] = 20020.0
    df.loc[first_after, ["high", "close"]] = 20080.0
    df.loc[first_after, "volume"] = 5000.0

    signals = OrbBreakFadeStrategy().generate_signals(df)
    assert signals.entries.loc[first_after] == 1
    assert signals.stop_price.loc[first_after] < df.loc[first_after, "close"]
    assert signals.stop_price.loc[first_after] <= 20020.0
    assert not np.isnan(signals.target_price.loc[first_after])


def test_orb_break_fade_fades_failed_break():
    df = _rth_day(n_bars=40, noise=0.0)
    minutes, _ = session_clock(df.index)
    or_mask = (minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 15)
    after_idx = df.index[minutes >= RTH_OPEN_MINUTES + 15]
    df.loc[or_mask, ["open", "low"]] = 20000.0
    df.loc[or_mask, ["close", "high"]] = 20020.0
    # Break attempt without volume, then close back inside the range.
    df.loc[after_idx[0], ["open", "low"]] = 20020.0
    df.loc[after_idx[0], ["high", "close"]] = 20060.0
    df.loc[after_idx[0], "volume"] = 500.0
    df.loc[after_idx[1], ["open", "high"]] = 20040.0
    df.loc[after_idx[1], ["low", "close"]] = 20010.0

    signals = OrbBreakFadeStrategy().generate_signals(df)
    assert signals.entries.loc[after_idx[0]] == 0
    assert signals.entries.loc[after_idx[1]] == -1
    assert signals.stop_price.loc[after_idx[1]] > df.loc[after_idx[1], "close"]


def test_orb_break_fade_signals_only_during_rth():
    df = _rth_day(start_et_minutes=8 * 60, n_bars=120, noise=0.0)
    signals = OrbBreakFadeStrategy().generate_signals(df)
    minutes, _ = session_clock(df.index)
    fired = signals.entries[signals.entries != 0]
    for ts in fired.index:
        assert minutes.loc[ts] >= RTH_OPEN_MINUTES
        assert minutes.loc[ts] < 15 * 60 + 30


def test_vol_squeeze_expansion_fires_on_release():
    # Tight pre-RTH + early-RTH coil, then a volume-backed upside release
    # still inside the 15:30 ET entry cutoff (130 × 5m from 04:00 ET → 14:45 ET).
    n = 130
    start = pd.Timestamp("2024-01-03 09:00", tz="UTC")  # 04:00 ET warmup
    idx = pd.date_range(start, periods=n, freq="5min", tz="UTC")
    close = np.full(n, 20000.0)
    close[-1] = 20080.0
    high = np.where(np.arange(n) == n - 1, 20085.0, close + 0.5)
    low = np.where(np.arange(n) == n - 1, 20000.0, close - 0.5)
    open_ = close.copy()
    open_[-1] = 20002.0
    volume = np.full(n, 800.0)
    volume[-1] = 8000.0
    df = pd.DataFrame({"open": open_, "high": high, "low": low, "close": close, "volume": volume}, index=idx)

    minutes, _ = session_clock(df.index)
    assert minutes.iloc[-1] >= 9 * 60 + 30
    assert minutes.iloc[-1] < 15 * 60 + 30

    strat = VolSqueezeExpansionStrategy(squeeze_lookback=40, squeeze_percentile=80, volume_mult=1.1)
    signals = strat.generate_signals(df)
    assert signals.entries.iloc[-1] == 1
    assert signals.stop_price.iloc[-1] < df["close"].iloc[-1]
    assert not np.isnan(signals.target_price.iloc[-1])


def test_impulse_clock_enters_large_range_bar():
    df = _rth_day(n_bars=40, noise=0.2)
    # Warmup keeps ATR small; last RTH bar is a large directional impulse.
    i = 25
    df.iloc[i, df.columns.get_loc("open")] = 20000.0
    df.iloc[i, df.columns.get_loc("low")] = 19995.0
    df.iloc[i, df.columns.get_loc("high")] = 20120.0
    df.iloc[i, df.columns.get_loc("close")] = 20110.0
    df.iloc[i, df.columns.get_loc("volume")] = 9000.0

    signals = ImpulseClockStrategy(impulse_atr_mult=1.2, volume_mult=1.0).generate_signals(df)
    assert signals.entries.iloc[i] == 1
    assert signals.stop_price.iloc[i] == df["low"].iloc[i]
    assert signals.target_price.iloc[i] > df["close"].iloc[i]


def test_impulse_clock_one_signal_per_session():
    df = _rth_day(n_bars=50, noise=0.2)
    for i in (20, 30):
        df.iloc[i, df.columns.get_loc("open")] = 20000.0
        df.iloc[i, df.columns.get_loc("low")] = 19990.0
        df.iloc[i, df.columns.get_loc("high")] = 20140.0
        df.iloc[i, df.columns.get_loc("close")] = 20120.0
        df.iloc[i, df.columns.get_loc("volume")] = 9000.0
    signals = ImpulseClockStrategy(impulse_atr_mult=1.2, volume_mult=1.0).generate_signals(df)
    assert (signals.entries != 0).sum() == 1


def test_new_strategies_use_risk_module_and_flatten():
    df = _rth_day(n_bars=80, noise=0.5)
    for name, strat in (
        ("orb", OrbBreakFadeStrategy()),
        ("squeeze", VolSqueezeExpansionStrategy(squeeze_lookback=40, squeeze_percentile=50)),
        ("impulse", ImpulseClockStrategy(impulse_atr_mult=1.2, volume_mult=1.0)),
    ):
        assert strat.flatten_rth is True
        assert strat.max_hold_bars is not None
        result = run_backtest(
            df=df, strategy=strat, symbol="MNQ", timeframe="5m",
            account_size=50_000, risk_pct=0.5,
        )
        for trade in result.trades:
            assert trade.contracts >= 1
            assert trade.exit_reason in {"stop", "target", "time_stop", "rth_flatten", "eod"}
            # Must not be open past the cash close.
            assert trade.exit_time.tz_convert("America/New_York").hour < 17
