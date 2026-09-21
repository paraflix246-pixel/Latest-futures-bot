#!/usr/bin/env python
"""
Massive-era research cycle: re-eval prior candidates + new families.

Protocol (locked):
  - Sprint-1 after engine (next-open fill, exit slip, gap-aware stops,
    RTH flatten, daily halt, contract cap).
  - Walk-forward 180d/60d on discovery (all bars before HOLDOUT_OOS_START).
  - Holdout once with constructor defaults (never WF winners).
  - Kill: MNQ WF OOS t < 2 OR MES WF t strongly negative (t < 0).
    Replication "not a clear loss" means MES t ≥ 0 preferred.

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
from src.strategies.vol_gated_ensemble import VolGatedEnsembleStrategy  # noqa: E402
from src.strategies.vol_squeeze_expansion import VolSqueezeExpansionStrategy  # noqa: E402

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
}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cycle", type=int, default=1)
    p.add_argument("--family", nargs="+", default=list(FAMILIES), choices=list(FAMILIES) + ["all"])
    p.add_argument("--symbol", nargs="+", default=[PRIMARY, REPLICATION])
    p.add_argument("--timeframe", default="5m")
    return p.parse_args()


def _t_from_trades(trades) -> float | None:
    from src.backtest.walk_forward import _t_stat

    return _t_stat([t.pnl for t in trades])


def run_holdout(df, strategy_cls, symbol, timeframe) -> Dict[str, Any]:
    strat = strategy_cls()
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


def verdict(mnq_wf: Dict[str, Any], mes_wf: Dict[str, Any] | None) -> str:
    t = mnq_wf.get("t_stat")
    n = mnq_wf.get("total_oos_trades") or 0
    if t is None or n < KILL_MIN_TRADES or t < KILL_T_STAT or not mnq_wf.get("significant"):
        return "KILLED (MNQ walk-forward OOS t<2 or under-traded)"
    if mes_wf is None:
        return "PENDING (MES not run)"
    mes_t = mes_wf.get("t_stat")
    if mes_t is None:
        return "KILLED (MES t missing)"
    if mes_t < 0:
        return "KILLED (MES replication is a clear loss, t<0)"
    return "SURVIVED kill gate (paper only — not a live go-ahead)"


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
        f"- WF: {WF_TRAIN_DAYS}d train / {WF_TEST_DAYS}d test",
        "",
        "## Metrics",
        "",
        "| Family | Kind | MNQ n | MNQ PnL | MNQ t | MES n | MES PnL | MES t | Holdout MNQ t | Verdict |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    by = {(r["symbol"], r["family"]): r for r in rows}
    families = sorted({r["family"] for r in rows})
    for name in families:
        mnq = by.get((PRIMARY, name), {})
        mes = by.get((REPLICATION, name), {})
        kind = FAMILIES[name][2]
        wf = mnq.get("walk_forward_oos", {})
        mes_wf = mes.get("walk_forward_oos", {})
        ho = mnq.get("holdout", {})
        lines.append(
            "| {name} | {kind} | {n} | {pnl} | {t} | {mn} | {mp} | {mt} | {ht} | {v} |".format(
                name=name,
                kind=kind,
                n=wf.get("total_oos_trades"),
                pnl=wf.get("total_oos_pnl"),
                t=wf.get("t_stat"),
                mn=mes_wf.get("total_oos_trades"),
                mp=mes_wf.get("total_oos_pnl"),
                mt=mes_wf.get("t_stat"),
                ht=ho.get("t_stat"),
                v=mnq.get("verdict", ""),
            )
        )
    lines.extend(["", "No live orders. Survivors still need GO_LIVE_CHECKLIST + founder OK.", ""])
    path.write_text("\n".join(lines))


def main() -> None:
    args = parse_args()
    families = list(FAMILIES) if "all" in args.family else args.family
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
                train_days=WF_TRAIN_DAYS,
                test_days=WF_TEST_DAYS,
                engine_kwargs=SPRINT1_AFTER_ENGINE,
            )
            oos = aggregate_oos(folds)
            print(f"  WF OOS {oos}", flush=True)
            hold = run_holdout(holdout, cls, symbol, args.timeframe)
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
        if mnq is None:
            continue
        mnq["verdict"] = verdict(
            mnq["walk_forward_oos"],
            mes["walk_forward_oos"] if mes else None,
        )
        (cycle_dir / f"{PRIMARY}_{name}.json").write_text(json.dumps(mnq, indent=2, default=str))
        if mes is not None:
            mes["verdict"] = mnq["verdict"]
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
    for r in rows:
        if r["symbol"] == PRIMARY:
            print(f"{r['family']:24} {r.get('verdict')}")


if __name__ == "__main__":
    main()
