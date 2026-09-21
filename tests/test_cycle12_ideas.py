"""Constructed-pattern tests for cycle-12 founder-idea modules."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd

from src.strategies.am_measured import AmMeasuredMoveStrategy
from src.strategies.cross_lead_open15 import CrossLeadOpen15Strategy
from src.strategies.first30_fade import First30FadeStrategy
from src.strategies.first5_break import First5BreakStrategy
from src.strategies.gap_on_confirm import GapOnConfirmStrategy
from src.strategies.gap_on_range import GapOnRangeStrategy
from src.strategies.lunch_or_magnet import LunchOrMagnetStrategy
from src.strategies.open_reject import OpenRejectStrategy
from src.strategies.overnight_gap_fade import OvernightGapFadeStrategy
from src.strategies.rvol_open15 import RvolOpen15Strategy
from src.strategies.session import FLATTEN_1545, RTH_OPEN_MINUTES, session_clock
from src.strategies.trend15_pullback5 import Trend15Pullback5Strategy
from src.strategies.vol_clock_fade import VolClockFadeStrategy
from src.strategies.weekday_gap_clock import WeekdayGapClockStrategy
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


def test_open_reject_fades_extreme_first15_close():
    df = _session(n_bars=78, price=20000.0)
    minutes, _ = session_clock(df.index)
    drive = df.index[(minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 15)]
    df.loc[drive[0], ["open", "low"]] = 20000.0
    df.loc[drive, "high"] = 20080.0
    df.loc[drive[-1], "close"] = 20075.0
    df.loc[drive[-1], "low"] = 20000.0
    entry = df.index[minutes == RTH_OPEN_MINUTES + 15][0]
    sig = OpenRejectStrategy(extreme_frac=0.25).generate_signals(df)
    assert sig.entries.loc[entry] == -1


def test_am_measured_enters_at_1000_with_range_target():
    df = _session(n_bars=78, price=20000.0)
    minutes, _ = session_clock(df.index)
    win = df.index[(minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 30)]
    df.loc[win[0], ["open", "low"]] = 20000.0
    df.loc[win, "high"] = 20050.0
    df.loc[win[-1], "close"] = 20040.0
    entry = df.index[minutes == RTH_OPEN_MINUTES + 30][0]
    sig = AmMeasuredMoveStrategy(min_body_atr=0.0).generate_signals(df)
    assert sig.entries.loc[entry] == 1
    assert sig.target_price.loc[entry] > df.loc[entry, "close"]


def test_trend15_chop_skip():
    df = _session(n_bars=78, price=20000.0)
    sig = Trend15Pullback5Strategy(adx_min=1000.0).generate_signals(df)
    assert int((sig.entries != 0).sum()) == 0


def test_weekday_gap_clock_skips_weekend_and_tiny_gap():
    df = _session(date="2024-01-03", n_bars=78, price=20000.0)  # Wednesday
    sig = WeekdayGapClockStrategy(min_gap_atr=10.0).generate_signals(df)
    assert int((sig.entries != 0).sum()) == 0
    assert WeekdayGapClockStrategy().weekdays == (1, 2, 3)


def test_weekday_gap_clock_takes_wednesday_gap_skips_friday():
    tue = _session(date="2024-01-02", n_bars=78, price=20000.0)
    wed = _session(date="2024-01-03", n_bars=78, price=20100.0)
    fri = _session(date="2024-01-05", n_bars=78, price=20200.0)
    df = pd.concat([tue, wed, fri])
    minutes, dates = session_clock(df.index)
    wed_open = df.index[(dates == pd.Timestamp("2024-01-03").date()) & (minutes == RTH_OPEN_MINUTES)][0]
    fri_open = df.index[(dates == pd.Timestamp("2024-01-05").date()) & (minutes == RTH_OPEN_MINUTES)][0]
    sig = WeekdayGapClockStrategy(min_gap_atr=0.0).generate_signals(df)
    assert sig.entries.loc[wed_open] == 1
    assert sig.entries.loc[fri_open] == 0


def _overnight_plus_rth(rth_open=20050.0, on_high=20100.0, on_low=19900.0):
    on_start = pd.Timestamp("2024-01-02 23:00", tz="UTC")  # 18:00 ET
    on_idx = pd.date_range(on_start, periods=30, freq="5min", tz="UTC")
    on = pd.DataFrame(
        {
            "open": np.full(30, 20000.0),
            "high": np.full(30, on_high),
            "low": np.full(30, on_low),
            "close": np.full(30, 20000.0),
            "volume": np.full(30, 500.0),
        },
        index=on_idx,
    )
    rth = _session(date="2024-01-03", n_bars=78, price=rth_open)
    return pd.concat([on, rth])


def test_gap_on_fill_only_fades_inside_range_and_skips_go():
    df = _overnight_plus_rth(rth_open=20050.0)
    minutes, dates = session_clock(df.index)
    day = pd.Timestamp("2024-01-03").date()
    open_bar = df.index[(dates == day) & (minutes == RTH_OPEN_MINUTES)][0]
    stretch = open_bar + pd.Timedelta(minutes=5)
    df.loc[stretch, "high"] = 20120.0
    df.loc[stretch, "close"] = 20040.0
    df.loc[stretch, "low"] = 20030.0
    fill = GapOnConfirmStrategy(trade_mode="fill", confirm_atr=0.0).generate_signals(df)
    assert fill.entries.loc[stretch] == -1
    go_time = df.index[(dates == day) & (minutes == RTH_OPEN_MINUTES + 15)][0]
    assert fill.entries.loc[go_time] == 0

    outside = _overnight_plus_rth(rth_open=20150.0)
    minutes, dates = session_clock(outside.index)
    drive = outside.index[(dates == day) & (minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 15)]
    outside.loc[drive[0], ["open", "low"]] = 20150.0
    outside.loc[drive[-1], ["high", "close"]] = 20200.0
    fill_out = GapOnConfirmStrategy(trade_mode="fill", confirm_atr=0.0).generate_signals(outside)
    assert int((fill_out.entries != 0).sum()) == 0
    both = GapOnConfirmStrategy(trade_mode="both", confirm_atr=0.0).generate_signals(outside)
    entry = outside.index[(dates == day) & (minutes == RTH_OPEN_MINUTES + 15)][0]
    assert both.entries.loc[entry] == 1


def test_cross_lead_open15_requires_agreement(monkeypatch):
    df = _session(n_bars=78, price=20000.0)
    minutes, _ = session_clock(df.index)
    drive = df.index[(minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 15)]
    df.loc[drive[0], ["open", "low"]] = 20000.0
    df.loc[drive[-1], ["high", "close"]] = 20080.0
    entry = df.index[minutes == RTH_OPEN_MINUTES + 15][0]
    d = pd.Timestamp("2024-01-03").date()
    monkeypatch.setattr(
        "src.strategies.cross_lead_open15._open15_bias_by_date",
        lambda symbol, tf: {d: 1},
    )
    agree = CrossLeadOpen15Strategy(lead_symbol="MES").generate_signals(df)
    assert agree.entries.loc[entry] == 1
    monkeypatch.setattr(
        "src.strategies.cross_lead_open15._open15_bias_by_date",
        lambda symbol, tf: {d: -1},
    )
    clash = CrossLeadOpen15Strategy(lead_symbol="MES").generate_signals(df)
    assert clash.entries.loc[entry] == 0


def test_vol_clock_fade_needs_open30_rvol_then_fades_vwap():
    days = []
    for i, d in enumerate(
        ["2024-01-02", "2024-01-03", "2024-01-04", "2024-01-05", "2024-01-08",
         "2024-01-09", "2024-01-10", "2024-01-11", "2024-01-12", "2024-01-16"]
    ):
        sess = _session(date=d, n_bars=78, price=20000.0 + i)
        days.append(sess)
    df = pd.concat(days)
    minutes, dates = session_clock(df.index)
    last = pd.Timestamp("2024-01-16").date()
    open30 = df.index[(dates == last) & (minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 30)]
    df.loc[open30, "volume"] = 9000.0
    after = df.index[(dates == last) & (minutes >= 11 * 60)][0]
    df.loc[after, "close"] = 20150.0
    df.loc[after, "high"] = 20160.0
    sig = VolClockFadeStrategy(rvol_mult=1.05, min_away_atr=0.0).generate_signals(df)
    assert sig.entries.loc[after] == -1
    quiet = VolClockFadeStrategy(rvol_mult=50.0, min_away_atr=0.0).generate_signals(df)
    assert int((quiet.entries != 0).sum()) == 0


def test_overnight_gap_fade_shorts_up_gap():
    tue = _session(date="2024-01-02", n_bars=78, price=20000.0)
    wed = _session(date="2024-01-03", n_bars=78, price=20100.0)
    df = pd.concat([tue, wed])
    minutes, dates = session_clock(df.index)
    wed_open = df.index[(dates == pd.Timestamp("2024-01-03").date()) & (minutes == RTH_OPEN_MINUTES)][0]
    sig = OvernightGapFadeStrategy(min_gap_atr=0.0).generate_signals(df)
    assert sig.entries.loc[wed_open] == -1


def test_first30_fade_shorts_up_drive():
    df = _session(n_bars=78, price=20000.0)
    minutes, _ = session_clock(df.index)
    drive = df.index[(minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 30)]
    df.loc[drive[0], ["open", "low"]] = 20000.0
    df.loc[drive[-1], ["high", "close"]] = 20080.0
    entry = df.index[minutes == RTH_OPEN_MINUTES + 30][0]
    sig = First30FadeStrategy(min_atr_frac=0.0).generate_signals(df)
    assert sig.entries.loc[entry] == -1
    quiet = First30FadeStrategy(min_atr_frac=10.0).generate_signals(df)
    assert quiet.entries.loc[entry] == 0


def test_lunch_or_magnet_fades_extended_open_range():
    df = _session(n_bars=78, price=20000.0)
    minutes, _ = session_clock(df.index)
    orb = df.index[(minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 30)]
    df.loc[orb, "high"] = 20020.0
    df.loc[orb, "low"] = 20000.0
    noon = df.index[minutes == 12 * 60][0]
    df.loc[noon, "close"] = 20100.0
    df.loc[noon, "high"] = 20110.0
    sig = LunchOrMagnetStrategy(min_away_atr=0.0).generate_signals(df)
    assert sig.entries.loc[noon] == -1
    assert sig.target_price.loc[noon] == 20010.0


def test_gap_on_go_only_skips_inside_range_fill():
    df = _overnight_plus_rth(rth_open=20050.0)
    minutes, dates = session_clock(df.index)
    day = pd.Timestamp("2024-01-03").date()
    stretch = df.index[(dates == day) & (minutes == RTH_OPEN_MINUTES)][0] + pd.Timedelta(minutes=5)
    df.loc[stretch, "high"] = 20120.0
    df.loc[stretch, "close"] = 20040.0
    go = GapOnConfirmStrategy(trade_mode="go", confirm_atr=0.0).generate_signals(df)
    assert int((go.entries != 0).sum()) == 0


def test_first5_break_enters_beyond_open_range():
    df = _session(n_bars=78, price=20000.0)
    minutes, _ = session_clock(df.index)
    first = df.index[minutes == RTH_OPEN_MINUTES][0]
    df.loc[first, "high"] = 20020.0
    df.loc[first, "low"] = 20000.0
    nxt = first + pd.Timedelta(minutes=5)
    df.loc[nxt, "close"] = 20080.0
    df.loc[nxt, "high"] = 20080.0
    sig = First5BreakStrategy(min_or_atr=0.0).generate_signals(df)
    assert sig.entries.loc[nxt] == 1
    inside = First5BreakStrategy(min_or_atr=10.0).generate_signals(df)
    assert inside.entries.loc[nxt] == 0
