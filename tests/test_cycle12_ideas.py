"""Constructed-pattern tests for cycle-12 founder-idea modules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.strategies.gap_on_range import GapOnRangeStrategy
from src.strategies.rvol_open15 import RvolOpen15Strategy
from src.strategies.session import FLATTEN_1545, RTH_OPEN_MINUTES, session_clock
from src.strategies.trend15_pullback5 import Trend15Pullback5Strategy
from src.strategies.vwap_first_hour import VwapFirstHourStrategy


def _session(date="2024-01-03", start_et_minutes=9 * 60 + 30, n_bars=78, price=20000.0):
    """Full RTH 5m session. January 2024 is EST (UTC-5)."""
    start_utc_hour = (start_et_minutes // 60) + 5
    start_utc_min = start_et_minutes % 60
    start = pd.Timestamp(f"{date} {start_utc_hour:02d}:{start_utc_min:02d}", tz="UTC")
    idx = pd.date_range(start, periods=n_bars, freq="5min", tz="UTC")
    closes = np.full(n_bars, float(price))
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


def test_vwap_first_hour_reclaims_during_hour_not_after():
    df = _session(n_bars=78, price=20000.0)
    minutes, _ = session_clock(df.index)
    first = df.index[minutes == RTH_OPEN_MINUTES][0]
    # Warmup 09:30–09:40: drive up so bias is long.
    df.loc[first, ["open", "low"]] = 20000.0
    df.loc[first, ["high", "close"]] = 20040.0
    df.loc[first + pd.Timedelta(minutes=5), ["open", "low"]] = 20040.0
    df.loc[first + pd.Timedelta(minutes=5), ["high", "close"]] = 20060.0
    reclaim = first + pd.Timedelta(minutes=10)  # 09:40, first trade bar
    df.loc[reclaim, "open"] = 20050.0
    df.loc[reclaim, "high"] = 20055.0
    df.loc[reclaim, "low"] = 20010.0  # trade through VWAP
    df.loc[reclaim, "close"] = 20050.0  # close back above

    signals = VwapFirstHourStrategy(warmup_minutes=10, allow_fail=False).generate_signals(df)
    assert signals.entries.loc[reclaim] == 1
    after_hour = df.index[minutes >= RTH_OPEN_MINUTES + 60]
    assert (signals.entries.loc[after_hour] == 0).all()
    assert VwapFirstHourStrategy().session_exit_minutes == FLATTEN_1545


def test_gap_on_range_fills_when_rth_open_inside_overnight():
    # Overnight 18:00 ET 2024-01-02 → 09:30 ET 2024-01-03 (EST = UTC-5).
    on_start = pd.Timestamp("2024-01-02 23:00", tz="UTC")  # 18:00 ET
    on_idx = pd.date_range(on_start, periods=30, freq="5min", tz="UTC")
    on = pd.DataFrame(
        {
            "open": np.full(30, 20000.0),
            "high": np.full(30, 20100.0),
            "low": np.full(30, 19900.0),
            "close": np.full(30, 20000.0),
            "volume": np.full(30, 500.0),
        },
        index=on_idx,
    )
    rth = _session(date="2024-01-03", n_bars=78, price=20050.0)
    df = pd.concat([on, rth])
    minutes, dates = session_clock(df.index)
    open_bar = df.index[(dates == pd.Timestamp("2024-01-03").date()) & (minutes == RTH_OPEN_MINUTES)][0]
    df.loc[open_bar, "open"] = 20050.0
    df.loc[open_bar, "close"] = 20048.0
    df.loc[open_bar, "high"] = 20055.0
    df.loc[open_bar, "low"] = 20045.0

    signals = GapOnRangeStrategy(min_inside_atr=0.0, min_outside_atr=0.0).generate_signals(df)
    assert signals.entries.loc[open_bar] == -1  # open above overnight mid → fade
    assert signals.target_price.loc[open_bar] == 20000.0


def test_rvol_dir_open15_fires_on_directional_close_and_flattens_1545():
    days = []
    for i, d in enumerate(["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05"]):
        sess = _session(date=d, n_bars=78, price=20000.0 + i)
        days.append(sess)
    df = pd.concat(days)
    minutes, dates = session_clock(df.index)
    last = pd.Timestamp("2024-01-05").date()
    drive = df.index[(dates == last) & (minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 15)]
    df.loc[drive, "volume"] = 9000.0
    df.loc[drive[0], ["open", "low"]] = 20000.0
    df.loc[drive[-1], ["high", "close"]] = 20080.0
    for ts in drive:
        df.loc[ts, "high"] = max(df.loc[ts, "high"], 20080.0)
        df.loc[ts, "low"] = min(df.loc[ts, "low"], 20000.0)
    entry = df.index[(dates == last) & (minutes == RTH_OPEN_MINUTES + 15)][0]

    strat = RvolOpen15Strategy(
        rvol_mult=1.0,
        min_atr_frac=0.0,
        min_body_pct=0.0,
        rvol_lookback=3,
        flatten_minutes=FLATTEN_1545,
    )
    signals = strat.generate_signals(df)
    assert strat.session_exit_minutes == FLATTEN_1545
    assert signals.entries.loc[entry] == 1


def test_trend15_chop_skip_with_huge_adx_min_has_no_entries():
    df = _session(n_bars=78, price=20000.0)
    sig = Trend15Pullback5Strategy(adx_min=1000.0).generate_signals(df)
    assert int((sig.entries != 0).sum()) == 0
