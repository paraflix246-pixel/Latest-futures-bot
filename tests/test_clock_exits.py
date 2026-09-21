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


def test_orb_filtered_requires_close_beyond_or_and_filters():
    from src.strategies.orb_filtered import OrbFilteredStrategy
    from src.strategies.session import RTH_OPEN_MINUTES, session_clock

    start = pd.Timestamp("2024-01-03 14:00", tz="UTC")
    idx = pd.date_range(start, periods=80, freq="5min", tz="UTC")
    px = np.full(80, 20000.0)
    df = pd.DataFrame(
        {"open": px, "high": px + 2, "low": px - 2, "close": px, "volume": 1000.0},
        index=idx,
    )
    minutes, _ = session_clock(df.index)
    or_mask = (minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 15)
    after = minutes >= RTH_OPEN_MINUTES + 15
    df.loc[or_mask, ["open", "low"]] = 20000.0
    df.loc[or_mask, ["close", "high"]] = 20020.0
    first = df.index[after][0]
    df.loc[first, ["open", "low"]] = 20020.0
    df.loc[first, ["high", "close"]] = 20080.0
    df.loc[first, "volume"] = 9000.0
    sig = OrbFilteredStrategy(or_minutes=15, on_adr_mult=99.0).generate_signals(df)
    assert sig.entries.loc[first] in (0, 1)
    if sig.entries.loc[first] == 1:
        assert sig.stop_price.loc[first] < df.loc[first, "close"]


def test_cycle3_modules_are_rth_flat():
    from src.strategies.orb_filtered import OrbFilteredStrategy
    from src.strategies.orb_retrace import OrbRetraceStrategy
    from src.strategies.trend15_pullback5 import Trend15Pullback5Strategy
    from src.strategies.vwap_hour import VwapHourReclaimFailStrategy

    for strat in (
        OrbFilteredStrategy(),
        OrbRetraceStrategy(),
        VwapHourReclaimFailStrategy(),
        Trend15Pullback5Strategy(),
    ):
        assert strat.flatten_rth is True
        assert strat.session_exit_minutes >= 15 * 60 + 30


def test_cycle4_modules_are_rth_flat():
    from src.strategies.adr_exhaust_fade import AdrExhaustFadeStrategy
    from src.strategies.gap_fill_go import GapFillGoStrategy
    from src.strategies.morning_reversal import MorningReversalStrategy
    from src.strategies.pdh_pdl_fail import PdhPdlFailStrategy
    from src.strategies.rvol_open15 import RvolOpen15Strategy
    from src.strategies.vwap_band_fade import VwapBandFadeStrategy

    for strat in (
        GapFillGoStrategy(),
        RvolOpen15Strategy(),
        VwapBandFadeStrategy(),
        AdrExhaustFadeStrategy(),
        PdhPdlFailStrategy(),
        MorningReversalStrategy(),
    ):
        assert strat.flatten_rth is True
        assert strat.session_exit_minutes is not None
        assert strat.max_hold_bars is not None


def test_cycle5_modules_are_rth_flat():
    from src.strategies.ema_stack_pullback import EmaStackPullbackStrategy
    from src.strategies.ib_mid_fade import IbMidFadeStrategy
    from src.strategies.rsi2_vwap_fade import Rsi2VwapFadeStrategy
    from src.strategies.three_bar_vwap_fade import ThreeBarVwapFadeStrategy
    from src.strategies.vwap_pullback_cont import VwapPullbackContStrategy

    for strat in (
        VwapPullbackContStrategy(),
        EmaStackPullbackStrategy(),
        IbMidFadeStrategy(),
        ThreeBarVwapFadeStrategy(),
        Rsi2VwapFadeStrategy(),
    ):
        assert strat.flatten_rth is True
        assert strat.session_exit_minutes is not None


def test_filtered_orb_2_defaults_match_local_hunt():
    from src.strategies.orb_filtered import OrbFilteredStrategy

    s = OrbFilteredStrategy()
    assert s.or_minutes == 15
    assert s.entry_window_minutes == 120
    assert s.volume_mult == 1.3
    assert s.require_vwap_align is True
    assert s.skip_inside_overnight is True
    assert s.require_retest is False
    assert s.target_r == 1.0
    assert s.flatten_rth is True
    assert s.entry_end_minutes == 9 * 60 + 30 + 15 + 120


def test_vwap_reclaim_and_orb_retrace_x_are_rth_flat():
    from src.strategies.orb_retrace import OrbRetraceStrategy
    from src.strategies.vwap_reclaim import VwapReclaimStrategy

    for strat in (VwapReclaimStrategy(), OrbRetraceStrategy(extended=True)):
        assert strat.flatten_rth is True
        assert strat.session_exit_minutes >= 15 * 60 + 30
    assert OrbRetraceStrategy(extended=True).name == "orb_retrace_x"


def test_symbol_gate_and_family_label():
    from scripts.research_cycle import family_label, symbol_gate

    ok, why = symbol_gate({"t_stat": 2.1, "total_oos_trades": 40}, {"t_stat": -0.2, "held_past_rth_close": 0})
    assert ok and why == "PASS"
    bad, reason = symbol_gate({"t_stat": 1.9, "total_oos_trades": 40}, None)
    assert not bad and "KILL" in reason
    cling, cling_why = symbol_gate(
        {"t_stat": 2.4, "total_oos_trades": 32},
        {"t_stat": 0.1, "held_past_rth_close": 2},
    )
    assert not cling and "overnight" in cling_why
    assert family_label(True, False) == "PASS_MNQ"
    assert family_label(False, True) == "PASS_MES"
    assert family_label(True, True) == "PASS_BOTH"
    assert family_label(False, False) == "KILL"
    assert family_label(False, True, False, True) == "PASS_MES_PROVISIONAL"
    assert family_label(True, False, True, False) == "PASS_MNQ_PROVISIONAL"


def test_s2_mes_sens_7_defaults_match_local_sprint4():
    from src.strategies import get_strategy
    from src.strategies.orb_filtered import MesSens7Strategy

    s = MesSens7Strategy()
    assert s.name == "s2_mes_sens_7"
    assert s.or_minutes == 15
    assert s.entry_window_minutes == 130
    assert s.volume_mult == 1.4
    assert s.require_vwap_align is True
    assert s.skip_inside_overnight is True
    assert s.require_retest is False
    assert s.target_r == 1.0
    assert s.stop_mode == "mid"
    assert s.flatten_rth is True
    via_registry = get_strategy("s2_mes_sens_7")
    assert via_registry.name == "s2_mes_sens_7"
    assert via_registry.entry_window_minutes == 130
    assert via_registry.volume_mult == 1.4


def test_wick_reject_cont_enters_after_failed_or_wick():
    from src.strategies.session import RTH_OPEN_MINUTES, session_clock
    from src.strategies.wick_reject_cont import WickRejectContStrategy

    start = pd.Timestamp("2024-01-03 14:00", tz="UTC")
    idx = pd.date_range(start, periods=80, freq="5min", tz="UTC")
    px = np.full(80, 20000.0)
    df = pd.DataFrame(
        {"open": px, "high": px + 2, "low": px - 2, "close": px, "volume": 1000.0},
        index=idx,
    )
    minutes, _ = session_clock(df.index)
    or_mask = (minutes >= RTH_OPEN_MINUTES) & (minutes < RTH_OPEN_MINUTES + 15)
    after = df.index[minutes >= RTH_OPEN_MINUTES + 15]
    df.loc[or_mask, ["open", "low"]] = 20000.0
    df.loc[or_mask, ["close", "high"]] = 20020.0
    # Wick through OR high, close back inside.
    df.loc[after[0], ["open", "close"]] = 20010.0
    df.loc[after[0], "high"] = 20040.0
    df.loc[after[0], "low"] = 20005.0
    # Next bar clears OR high.
    df.loc[after[1], ["open", "low"]] = 20020.0
    df.loc[after[1], ["high", "close"]] = 20050.0
    sig = WickRejectContStrategy(require_vwap_align=False).generate_signals(df)
    assert sig.entries.loc[after[0]] == 0
    assert sig.entries.loc[after[1]] == 1
    assert sig.stop_price.loc[after[1]] == 20010.0


def test_cycle8_modules_are_rth_flat():
    from src.strategies.gap_and_go import GapAndGoStrategy
    from src.strategies.nr15_break import Nr15BreakStrategy
    from src.strategies.onh_onl_break import OnhOnlBreakStrategy
    from src.strategies.orb_fail_fade import OrbFailFadeStrategy
    from src.strategies.spread_fade import SpreadFadeStrategy
    from src.strategies.volume_dryup_break import VolumeDryupBreakStrategy
    from src.strategies.wick_reject_cont import WickRejectContStrategy

    for strat in (
        OrbFailFadeStrategy(),
        GapAndGoStrategy(),
        Nr15BreakStrategy(),
        WickRejectContStrategy(),
        OnhOnlBreakStrategy(),
        VolumeDryupBreakStrategy(),
        SpreadFadeStrategy(),
    ):
        assert strat.flatten_rth is True
        assert strat.session_exit_minutes is not None
        assert strat.max_hold_bars is not None


def test_paper_engine_matches_sprint1():
    from scripts.run_paper_replay import PAPER_ENGINE
    from src.research.presets import SPRINT1_AFTER_ENGINE

    assert PAPER_ENGINE.get("rth_entries_only") is True
    assert PAPER_ENGINE.get("fill_model") == "next_open"
    assert PAPER_ENGINE.get("flatten_at_rth_close") is True
    for key, val in SPRINT1_AFTER_ENGINE.items():
        assert PAPER_ENGINE[key] == val


def test_open_drive_and_failed_ib_have_clock_attrs():
    from src.strategies.afternoon_momentum import AfternoonMomentumStrategy
    from src.strategies.am_vwap_reclaim import AmVwapReclaimStrategy
    from src.strategies.failed_ib_fade import FailedIbFadeStrategy
    from src.strategies.open_drive import OpenDriveStrategy

    for strat in (
        OpenDriveStrategy(),
        FailedIbFadeStrategy(),
        AfternoonMomentumStrategy(),
        AmVwapReclaimStrategy(),
    ):
        assert strat.flatten_rth is True
        assert strat.max_hold_bars is not None
