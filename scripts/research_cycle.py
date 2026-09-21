#!/usr/bin/env python
"""
Massive-era research cycle: re-eval prior candidates + new families.

Protocol (locked):
  - Sprint-1 after engine (next-open fill, exit slip, gap-aware stops,
    RTH flatten, daily halt, contract cap).
  - Walk-forward 180d/60d on discovery (all bars before HOLDOUT_OOS_START).
  - Holdout once with constructor defaults (never WF winners).
  - Per-symbol gate (founder 2026-09-21): WF OOS t ≥ 2.0, n ≥ 30,
    holdout not strongly negative (t ≥ −1.0), no overnight cling.
  - PASS_MNQ / PASS_MES are independent. Same logic/params on both is
    NOT required. PASS_BOTH is a bonus. MNQ-only is an acceptable candidate.
  - KILL: in-sample only, overnight cling, fabricated data, live trading.

Usage:
    python scripts/research_cycle.py --cycle 1
    python scripts/research_cycle.py --cycle 1 --family ensemble last30_momentum
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import REPORTS_DIR  # noqa: E402
from src.backtest.engine import run_backtest  # noqa: E402
from src.backtest.metrics import compute_metrics  # noqa: E402
from src.backtest.walk_forward import aggregate_oos, walk_forward_search  # noqa: E402
from src.data.loader import load_ohlcv  # noqa: E402
from src.research.presets import (  # noqa: E402
    ACCOUNT_SIZE,
    HOLDOUT_OOS_START,
    KILL_MIN_TRADES,
    KILL_T_STAT,
    PRIMARY,
    REPLICATION,
    RISK_PCT,
    SPRINT1_AFTER_ENGINE,
    WF_TEST_DAYS,
    WF_TRAIN_DAYS,
)
from src.strategies.ensemble import EnsembleStrategy  # noqa: E402
from src.strategies.ib_extension import IbExtensionStrategy  # noqa: E402
from src.strategies.impulse_clock import ImpulseClockStrategy  # noqa: E402
from src.strategies.last30_momentum import Last30MomentumStrategy  # noqa: E402
from src.strategies.lunch_range_break import LunchRangeBreakStrategy  # noqa: E402
from src.strategies.on_inventory import OnInventoryStrategy  # noqa: E402
from src.strategies.orb_crabel import OrbCrabelStrategy  # noqa: E402
from src.strategies.afternoon_momentum import AfternoonMomentumStrategy  # noqa: E402
from src.strategies.am_vwap_reclaim import AmVwapReclaimStrategy  # noqa: E402
from src.strategies.failed_ib_fade import FailedIbFadeStrategy  # noqa: E402
from src.strategies.open_drive import OpenDriveStrategy  # noqa: E402
from src.strategies.orb_filtered import OrbFilteredStrategy  # noqa: E402
from src.strategies.orb_retrace import OrbRetraceStrategy  # noqa: E402
from src.strategies.trend15_pullback5 import Trend15Pullback5Strategy  # noqa: E402
from src.strategies.vol_gated_ensemble import VolGatedEnsembleStrategy  # noqa: E402
from src.strategies.vol_squeeze_expansion import VolSqueezeExpansionStrategy  # noqa: E402
from src.strategies.vwap_hour import VwapHourReclaimFailStrategy  # noqa: E402
from src.strategies.gap_fill_go import GapFillGoStrategy  # noqa: E402
from src.strategies.rvol_open15 import RvolOpen15Strategy  # noqa: E402
from src.strategies.vwap_band_fade import VwapBandFadeStrategy  # noqa: E402
from src.strategies.adr_exhaust_fade import AdrExhaustFadeStrategy  # noqa: E402
from src.strategies.pdh_pdl_fail import PdhPdlFailStrategy  # noqa: E402
from src.strategies.morning_reversal import MorningReversalStrategy  # noqa: E402
from src.strategies.vwap_reclaim import VwapReclaimStrategy  # noqa: E402
from src.strategies.vwap_pullback_cont import VwapPullbackContStrategy  # noqa: E402
from src.strategies.ema_stack_pullback import EmaStackPullbackStrategy  # noqa: E402
from src.strategies.ib_mid_fade import IbMidFadeStrategy  # noqa: E402
from src.strategies.three_bar_vwap_fade import ThreeBarVwapFadeStrategy  # noqa: E402
from src.strategies.rsi2_vwap_fade import Rsi2VwapFadeStrategy  # noqa: E402

FAMILIES = {
    "ensemble": (
        EnsembleStrategy,
        {"rth_only": [True], "breakout_in_range": [False], "event_trigger": [True]},
        "prior",
    ),
    "orb_crabel": (
        OrbCrabelStrategy,
        {"or_minutes": [15, 30], "rvol_mult": [1.5, 2.0]},
        "prior",
    ),
    "last30_momentum": (
        Last30MomentumStrategy,
        {"min_ret_atr_frac": [0.10, 0.20], "stop_atr_mult": [0.25, 0.40]},
        "prior",
    ),
    "vol_squeeze_expansion": (
        VolSqueezeExpansionStrategy,
        {"squeeze_percentile": [15, 25], "volume_mult": [1.2, 1.5]},
        "prior",
    ),
    "impulse_clock": (
        ImpulseClockStrategy,
        {"impulse_atr_mult": [1.5, 2.0], "max_hold_bars": [6, 12]},
        "prior",
    ),
    "vol_gated_ensemble": (
        VolGatedEnsembleStrategy,
        {"atr_pct_lo": [15.0, 25.0], "atr_pct_hi": [75.0, 85.0]},
        "new",
    ),
    "ib_extension": (
        IbExtensionStrategy,
        {"ib_minutes": [60], "volume_mult": [1.1, 1.4]},
        "new",
    ),
    "on_inventory": (
        OnInventoryStrategy,
        {"on_atr_min": [0.15, 0.25], "stop_atr_mult": [0.30, 0.45]},
        "new",
    ),
    "lunch_range_break": (
        LunchRangeBreakStrategy,
        {"lunch_atr_max": [0.35, 0.50], "volume_mult": [1.0, 1.3]},
        "new",
    ),
    "open_drive": (
        OpenDriveStrategy,
        {"min_atr_frac": [0.10, 0.20], "stop_atr_mult": [0.25, 0.40]},
        "new",
    ),
    "failed_ib_fade": (
        FailedIbFadeStrategy,
        {"failure_bars": [3, 5], "target_ib_mult": [1.0, 1.5]},
        "new",
    ),
    "afternoon_momentum": (
        AfternoonMomentumStrategy,
        {"min_atr_frac": [0.08, 0.16], "stop_atr_mult": [0.25, 0.40]},
        "new",
    ),
    "am_vwap_reclaim": (
        AmVwapReclaimStrategy,
        {"stop_atr_mult": [0.25, 0.45]},
        "new",
    ),
    # Cycle 3: same constructor params on MNQ and MES (single-combo grids).
    "orb_filtered_15": (OrbFilteredStrategy, {"or_minutes": [15], "retest": [False]}, "new"),
    "orb_filtered_5": (OrbFilteredStrategy, {"or_minutes": [5], "retest": [False]}, "new"),
    "orb_filtered_30": (OrbFilteredStrategy, {"or_minutes": [30], "retest": [False]}, "new"),
    "orb_filtered_retest": (OrbFilteredStrategy, {"or_minutes": [15], "retest": [True]}, "new"),
    "orb_retrace": (OrbRetraceStrategy, {}, "new"),
    "vwap_hour_reclaim_fail": (VwapHourReclaimFailStrategy, {}, "new"),
    "trend15_pullback5": (Trend15Pullback5Strategy, {}, "new"),
    # Cycle 4: independent per-symbol edges (params may differ by symbol).
    "gap_fill_go": (
        GapFillGoStrategy,
        {"min_gap_atr": [0.30, 0.50], "stop_atr_mult": [0.30, 0.45]},
        "new",
    ),
    "rvol_open15": (
        RvolOpen15Strategy,
        {"rvol_mult": [1.3, 1.8], "min_atr_frac": [0.08, 0.15]},
        "new",
    ),
    "vwap_band_fade": (
        VwapBandFadeStrategy,
        {"band_atr": [0.30, 0.50], "stop_atr_mult": [0.25, 0.40]},
        "new",
    ),
    "adr_exhaust_fade": (
        AdrExhaustFadeStrategy,
        {"exhaust_mult": [0.75, 1.00], "stop_atr_mult": [0.20, 0.35]},
        "new",
    ),
    "pdh_pdl_fail": (
        PdhPdlFailStrategy,
        {"stop_atr_mult": [0.15, 0.30]},
        "new",
    ),
    "morning_reversal": (
        MorningReversalStrategy,
        {"stop_atr_mult": [0.15, 0.30]},
        "new",
    ),
    "vwap_pullback_cont": (
        VwapPullbackContStrategy,
        {"align_bars": [4, 8], "stop_atr_mult": [0.25, 0.40]},
        "new",
    ),
    "ema_stack_pullback": (
        EmaStackPullbackStrategy,
        {"stop_atr_mult": [0.25, 0.45]},
        "new",
    ),
    "ib_mid_fade": (
        IbMidFadeStrategy,
        {"ext_atr": [0.25, 0.45], "stop_atr_mult": [0.25, 0.40]},
        "new",
    ),
    "three_bar_vwap_fade": (
        ThreeBarVwapFadeStrategy,
        {"stop_atr_mult": [0.20, 0.35]},
        "new",
    ),
    "rsi2_vwap_fade": (
        Rsi2VwapFadeStrategy,
        {"rsi_lo": [5.0, 15.0], "stop_atr_mult": [0.25, 0.40]},
        "new",
    ),
    "orb_filtered_am": (
        OrbFilteredStrategy,
        {"or_minutes": [15], "retest": [False], "volume_mult": [1.5], "entry_end_minutes": [11 * 60 + 30]},
        "new",
    ),
    "trend15_breakeven": (
        Trend15Pullback5Strategy,
        {"stop_atr_mult": [0.30, 0.50], "breakeven_r_mult": [0.7]},
        "new",
    ),
    "on_inventory_loose": (
        OnInventoryStrategy,
        {"on_atr_min": [0.08, 0.12], "stop_atr_mult": [0.30, 0.45]},
        "new",
    ),
    # Cycle 6: official port of local-hunt filtered_orb / vwap_reclaim / orb_retrace.
    "filtered_orb_2": (
        OrbFilteredStrategy,
        {
            "or_minutes": [15],
            "entry_window_minutes": [120],
            "volume_mult": [1.3],
            "require_vwap_align": [True],
            "skip_inside_overnight": [True],
            "require_retest": [False],
            "target_r": [1.0],
        },
        "hunt",
    ),
    "filtered_orb_90": (
        OrbFilteredStrategy,
        {
            "or_minutes": [15],
            "entry_window_minutes": [75],
            "volume_mult": [1.3],
            "require_vwap_align": [True],
            "skip_inside_overnight": [True],
            "entry_end_minutes": [11 * 60],
        },
        "hunt",
    ),
    "filtered_orb_5m": (
        OrbFilteredStrategy,
        {
            "or_minutes": [5],
            "entry_window_minutes": [120],
            "volume_mult": [1.3],
            "require_vwap_align": [True],
            "skip_inside_overnight": [True],
        },
        "hunt",
    ),
    "filtered_orb_adx": (
        OrbFilteredStrategy,
        {
            "or_minutes": [15],
            "entry_window_minutes": [120],
            "volume_mult": [1.3],
            "adx_min": [18.0, 25.0],
            "stop_mode": ["mid", "atr"],
            "stop_atr_mult": [0.20],
        },
        "hunt",
    ),
    "vwap_reclaim": (
        VwapReclaimStrategy,
        {
            "min_away_atr": [0.10, 0.15, 0.20],
            "stop_atr_mult": [0.20, 0.30, 0.40],
            "entry_end_minutes": [11 * 60, 15 * 60 + 45],
        },
        "hunt",
    ),
    "vwap_reclaim_90": (
        VwapReclaimStrategy,
        {
            "min_away_atr": [0.10, 0.20],
            "stop_atr_mult": [0.20, 0.30],
            "entry_end_minutes": [11 * 60],
            "first_hour_bias": [True, False],
        },
        "hunt",
    ),
    "orb_retrace_3": (
        OrbRetraceStrategy,
        {
            "or_minutes": [15],
            "entry_window_minutes": [120],
            "skip_inside_overnight": [True],
            "require_vwap_align": [True],
            "extended": [False],
        },
        "hunt",
    ),
    "orb_retrace_x": (
        OrbRetraceStrategy,
        {
            "or_minutes": [15, 5],
            "entry_window_minutes": [120, 180],
            "extended": [True],
            "stop_mode": ["opposite", "atr"],
            "stop_atr_mult": [0.20],
        },
        "hunt",
    ),
}

CYCLE_DEFAULTS = {
    1: [
        "ensemble", "orb_crabel", "last30_momentum", "vol_squeeze_expansion",
        "impulse_clock", "vol_gated_ensemble", "ib_extension", "on_inventory",
        "lunch_range_break",
    ],
    2: ["open_drive", "failed_ib_fade", "afternoon_momentum", "am_vwap_reclaim"],
    3: [
        "orb_filtered_15", "orb_filtered_5", "orb_filtered_30", "orb_filtered_retest",
        "orb_retrace", "vwap_hour_reclaim_fail", "trend15_pullback5",
    ],
    4: [
        "gap_fill_go", "rvol_open15", "vwap_band_fade",
        "adr_exhaust_fade", "pdh_pdl_fail", "morning_reversal",
    ],
    5: [
        "vwap_pullback_cont", "ema_stack_pullback", "ib_mid_fade",
        "three_bar_vwap_fade", "rsi2_vwap_fade", "orb_filtered_am",
        "trend15_breakeven", "on_inventory_loose",
    ],
    6: [
        "filtered_orb_2", "filtered_orb_90", "filtered_orb_5m", "filtered_orb_adx",
        "vwap_reclaim", "vwap_reclaim_90", "orb_retrace_3", "orb_retrace_x",
    ],
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cycle", type=int, default=1)
    p.add_argument("--family", nargs="+", default=None, choices=list(FAMILIES) + ["all"])
    p.add_argument("--symbol", nargs="+", default=[PRIMARY, REPLICATION])
    p.add_argument("--timeframe", default="5m")
    p.add_argument("--train-days", type=int, default=WF_TRAIN_DAYS)
    p.add_argument("--test-days", type=int, default=WF_TEST_DAYS)
    return p.parse_args()


def _t_from_trades(trades) -> float | None:
    from src.backtest.walk_forward import _t_stat

    return _t_stat([t.pnl for t in trades])


def _locked_params(grid: dict) -> dict:
    """Single-combo grids → identical constructor kwargs on MNQ and MES."""
    return {k: v[0] for k, v in grid.items()} if grid else {}


def run_holdout(df, strategy_cls, symbol, timeframe, params: dict | None = None) -> Dict[str, Any]:
    strat = strategy_cls(**(params or {}))
    result = run_backtest(
        df, strat, symbol, timeframe, ACCOUNT_SIZE, RISK_PCT, **SPRINT1_AFTER_ENGINE
    )
    metrics = compute_metrics(result, ACCOUNT_SIZE)
    t_stat = _t_from_trades(result.trades)
    metrics["t_stat"] = round(t_stat, 3) if t_stat is not None else None
    metrics["exit_reasons"] = dict(Counter(t.exit_reason for t in result.trades))
    overnight = 0
    for t in result.trades:
        local_exit = t.exit_time.tz_convert("America/New_York")
        if local_exit.hour > 16 or (local_exit.hour == 16 and local_exit.minute > 5):
            overnight += 1
    metrics["held_past_rth_close"] = overnight
    return metrics


HOLDOUT_STRONG_NEG = -1.0


def symbol_gate(wf: Dict[str, Any], ho: Dict[str, Any] | None) -> tuple[bool, str]:
    """Per-symbol gate. MNQ-only is an acceptable candidate (PASS_MNQ)."""
    t = wf.get("t_stat")
    n = wf.get("total_oos_trades") or 0
    if t is None or n < KILL_MIN_TRADES or t < KILL_T_STAT:
        return False, "KILL (WF t<2 or n<30)"
    if ho:
        ht = ho.get("t_stat")
        if ht is not None and ht < HOLDOUT_STRONG_NEG:
            return False, f"KILL (holdout strongly negative t={ht})"
        if int(ho.get("held_past_rth_close") or 0) > 0:
            return False, "KILL (overnight cling)"
    return True, "PASS"


def family_label(mnq_ok: bool, mes_ok: bool) -> str:
    if mnq_ok and mes_ok:
        return "PASS_BOTH"
    if mnq_ok:
        return "PASS_MNQ"
    if mes_ok:
        return "PASS_MES"
    return "KILL"


def data_span(df: pd.DataFrame) -> Dict[str, Any]:
    return {
        "rows": int(len(df)),
        "start": str(df.index[0]) if len(df) else None,
        "end": str(df.index[-1]) if len(df) else None,
        "source": "data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)",
    }


def write_cycle_md(path: Path, cycle: int, rows: List[Dict[str, Any]], spans: Dict[str, Any]) -> None:
    lines = [
        f"# Research cycle {cycle}",
        "",
        "Paper / backtest only. Sprint-1 realistic fills. No live trading.",
        "",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "## Tape",
        "",
        f"- MNQ: `{spans.get('MNQ')}`",
        f"- MES: `{spans.get('MES')}`",
        f"- Holdout start (locked): `{HOLDOUT_OOS_START}`",
        f"- WF: see run log (default {WF_TRAIN_DAYS}d/{WF_TEST_DAYS}d)",
        "",
        "## Metrics",
        "",
        "| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |",
        "|---|---|---:|---:|---:|---|---:|---:|---:|---|---|",
    ]
    by = {(r["symbol"], r["family"]): r for r in rows}
    families = sorted({r["family"] for r in rows})
    for name in families:
        mnq = by.get((PRIMARY, name), {})
        mes = by.get((REPLICATION, name), {})
        kind = FAMILIES.get(name, (None, None, "new"))[2]
        wf = mnq.get("walk_forward_oos", {})
        mes_wf = mes.get("walk_forward_oos", {})
        ho = mnq.get("holdout", {})
        mes_ho = mes.get("holdout", {})
        lines.append(
            "| {name} | {kind} | {n} | {t} | {ht} | {mv} | {mn} | {mt} | {mht} | {mev} | {v} |".format(
                name=name,
                kind=kind,
                n=wf.get("total_oos_trades"),
                t=wf.get("t_stat"),
                ht=ho.get("t_stat"),
                mv=mnq.get("symbol_verdict", ""),
                mn=mes_wf.get("total_oos_trades"),
                mt=mes_wf.get("t_stat"),
                mht=mes_ho.get("t_stat"),
                mev=mes.get("symbol_verdict", ""),
                v=mnq.get("verdict", mes.get("verdict", "")),
            )
        )
    lines.extend(
        [
            "",
            "Labels: **PASS_MNQ** (MNQ-only candidate, trade-MNQ-only is allowed), "
            "**PASS_MES**, **PASS_BOTH**, **KILL**. Paper only. No live trading.",
            "",
        ]
    )
    path.write_text("\n".join(lines))


def main() -> None:
    args = parse_args()
    if args.family is None:
        families = CYCLE_DEFAULTS.get(args.cycle, list(FAMILIES))
    elif "all" in args.family:
        families = list(FAMILIES)
    else:
        families = args.family
    cycle_dir = Path(__file__).resolve().parent.parent / REPORTS_DIR / "cycles" / f"cycle_{args.cycle}"
    cycle_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    spans = {}
    payloads = {}

    for symbol in args.symbol:
        df = load_ohlcv(symbol, args.timeframe)
        spans[symbol] = data_span(df)
        cut = pd.Timestamp(HOLDOUT_OOS_START, tz=df.index.tz)
        discovery = df[df.index < cut]
        holdout = df[df.index >= cut]
        print(
            f"\n=== {symbol} {args.timeframe} discovery={len(discovery)} "
            f"holdout={len(holdout)} {spans[symbol]['start']} -> {spans[symbol]['end']} ===",
            flush=True,
        )
        for name in families:
            cls, grid, kind = FAMILIES[name]
            print(f"-- {symbol} / {name} ({kind}) WF --", flush=True)
            folds = walk_forward_search(
                df=discovery,
                strategy_cls=cls,
                param_grid=grid,
                symbol=symbol,
                timeframe=args.timeframe,
                account_size=ACCOUNT_SIZE,
                risk_pct=RISK_PCT,
                train_days=args.train_days,
                test_days=args.test_days,
                engine_kwargs=SPRINT1_AFTER_ENGINE,
            )
            oos = aggregate_oos(folds)
            print(f"  WF OOS {oos}", flush=True)
            locked = _locked_params(grid)
            hold = run_holdout(holdout, cls, symbol, args.timeframe, params=locked)
            print(f"  Holdout {hold.get('total_pnl')} t={hold.get('t_stat')} n={hold.get('trade_count')}", flush=True)
            payload = {
                "cycle": args.cycle,
                "symbol": symbol,
                "family": name,
                "kind": kind,
                "tape": spans[symbol],
                "engine": SPRINT1_AFTER_ENGINE,
                "walk_forward_oos": oos,
                "folds": [
                    {
                        "fold": f.fold,
                        "train_start": str(f.train_start),
                        "train_end": str(f.train_end),
                        "test_start": str(f.test_start),
                        "test_end": str(f.test_end),
                        "best_params": f.best_params,
                        "train_metrics": f.train_metrics,
                        "test_metrics": f.test_metrics,
                    }
                    for f in folds
                ],
                "holdout": hold,
            }
            payloads[(symbol, name)] = payload
            (cycle_dir / f"{symbol}_{name}.json").write_text(json.dumps(payload, indent=2, default=str))

    for name in families:
        mnq = payloads.get((PRIMARY, name))
        mes = payloads.get((REPLICATION, name))
        mnq_ok = mes_ok = False
        if mnq is not None:
            mnq_ok, mnq_sv = symbol_gate(mnq["walk_forward_oos"], mnq.get("holdout"))
            mnq["symbol_verdict"] = f"PASS_MNQ" if mnq_ok else mnq_sv
        if mes is not None:
            mes_ok, mes_sv = symbol_gate(mes["walk_forward_oos"], mes.get("holdout"))
            mes["symbol_verdict"] = f"PASS_MES" if mes_ok else mes_sv
        label = family_label(mnq_ok, mes_ok)
        if mnq is not None:
            mnq["verdict"] = label
            (cycle_dir / f"{PRIMARY}_{name}.json").write_text(json.dumps(mnq, indent=2, default=str))
        if mes is not None:
            mes["verdict"] = label
            (cycle_dir / f"{REPLICATION}_{name}.json").write_text(json.dumps(mes, indent=2, default=str))
        rows.extend([r for r in (mnq, mes) if r])

    write_cycle_md(cycle_dir / "SUMMARY.md", args.cycle, rows, spans)
    board = [
        {
            "family": r["family"],
            "symbol": r["symbol"],
            "verdict": r.get("verdict"),
            **r["walk_forward_oos"],
            "holdout_t": r["holdout"].get("t_stat"),
            "holdout_pnl": r["holdout"].get("total_pnl"),
        }
        for r in rows
    ]
    (cycle_dir / "leaderboard.json").write_text(json.dumps(board, indent=2))
    print(f"\nWrote {cycle_dir}")
    seen = set()
    for r in rows:
        key = r["family"]
        if key in seen:
            continue
        seen.add(key)
        print(f"{key:28} {r.get('verdict')}")


if __name__ == "__main__":
    main()
