#!/usr/bin/env python
"""
Sprint improve-loop runner: baseline / after / compare for MNQ 5m ensemble
plus the three component strategies (trend, mean_reversion, breakout).

Walk-forward (180d train / 60d test) and a locked chronological holdout.
Does not claim an edge; writes honest IS vs OOS metrics under reports/sprint1/.

Example:
    python scripts/run_sprint.py --phase before
    python scripts/run_sprint.py --phase after
    python scripts/run_sprint.py --phase compare
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DEFAULT_ACCOUNT_SIZE, DEFAULT_RISK_PCT, REPORTS_DIR  # noqa: E402
from src.backtest.engine import run_backtest  # noqa: E402
from src.backtest.metrics import compute_metrics  # noqa: E402
from src.backtest.walk_forward import aggregate_oos, walk_forward_search  # noqa: E402
from src.data.loader import load_ohlcv  # noqa: E402
from src.strategies.breakout import BreakoutStrategy  # noqa: E402
from src.strategies.ensemble import EnsembleStrategy  # noqa: E402
from src.strategies.mean_reversion import MeanReversionStrategy  # noqa: E402
from src.strategies.trend_following import TrendFollowingStrategy  # noqa: E402

SPRINT_DIR = Path(__file__).resolve().parent.parent / REPORTS_DIR / "sprint1"
STRATEGIES = ["trend", "mean_reversion", "breakout", "ensemble"]
HOLDOUT_OOS_START = "2025-09-12"  # locked; never used for choosing the sprint fixes
WF_TRAIN_DAYS = 180
WF_TEST_DAYS = 60
ACCOUNT = DEFAULT_ACCOUNT_SIZE
RISK_PCT = DEFAULT_RISK_PCT

STRATEGY_CLASSES = {
    "trend": TrendFollowingStrategy,
    "mean_reversion": MeanReversionStrategy,
    "breakout": BreakoutStrategy,
    "ensemble": EnsembleStrategy,
}

def _strategy(name: str, phase: str):
    if phase == "before":
        builders = {
            "trend": lambda: TrendFollowingStrategy(),
            "mean_reversion": lambda: MeanReversionStrategy(event_trigger=False),
            "breakout": lambda: BreakoutStrategy(event_trigger=False),
            "ensemble": lambda: EnsembleStrategy(
                rth_only=False, breakout_in_range=True, event_trigger=False
            ),
        }
    else:
        builders = {
            "trend": lambda: TrendFollowingStrategy(),
            "mean_reversion": lambda: MeanReversionStrategy(event_trigger=True),
            "breakout": lambda: BreakoutStrategy(event_trigger=True),
            "ensemble": lambda: EnsembleStrategy(
                rth_only=True, breakout_in_range=False, event_trigger=True
            ),
        }
    return builders[name]()


def _strategy_ctor_kwargs(name: str, phase: str) -> dict:
    """Single-combo param grid so walk-forward instantiates the phase's defaults."""
    if name == "trend":
        return {}
    if phase == "before":
        if name == "mean_reversion":
            return {"event_trigger": [False]}
        if name == "breakout":
            return {"event_trigger": [False]}
        if name == "ensemble":
            return {"rth_only": [False], "breakout_in_range": [True], "event_trigger": [False]}
    else:
        if name == "mean_reversion":
            return {"event_trigger": [True]}
        if name == "breakout":
            return {"event_trigger": [True]}
        if name == "ensemble":
            return {"rth_only": [True], "breakout_in_range": [False], "event_trigger": [True]}
    return {}


def _engine_kwargs(phase: str) -> Dict[str, Any]:
    """Realistic overlays are opt-in for the after phase so `before` matches
    the pre-sprint engine (signal-close fill, no daily halt, no flatten)."""
    try:
        from src.backtest.engine import ENGINE_DEFAULTS  # type: ignore
    except Exception:
        ENGINE_DEFAULTS = {}
    if phase == "before":
        kwargs = {}
        if ENGINE_DEFAULTS:
            kwargs.update(
                {
                    "fill_model": "signal_close",
                    "apply_exit_slippage": False,
                    "gap_aware_stops": False,
                    "trail_update": "same_bar",
                    "cooldown_bars": 0,
                    "allow_same_bar_reentry": True,
                    "daily_loss_halt_pct": None,
                    "flatten_at_rth_close": False,
                    "max_contracts": None,
                }
            )
        return kwargs
    kwargs = dict(ENGINE_DEFAULTS) if ENGINE_DEFAULTS else {}
    kwargs.update(
        {
            "fill_model": "next_open",
            "apply_exit_slippage": True,
            "gap_aware_stops": True,
            "trail_update": "next_bar",
            "cooldown_bars": 3,
            "allow_same_bar_reentry": False,
            "daily_loss_halt_pct": 2.0,
            "flatten_at_rth_close": True,
            "max_contracts": 10,
        }
    )
    return kwargs


def _extra_metrics(result, account_size: float) -> Dict[str, Any]:
    trades = result.trades
    base = compute_metrics(result, account_size)
    if not trades:
        base.update(
            {
                "total_gross_pnl": 0.0,
                "total_commission": 0.0,
                "total_slippage": 0.0,
                "avg_hold_minutes": None,
                "median_hold_minutes": None,
                "avg_contracts": None,
                "max_contracts": 0,
                "same_bar_reentries": 0,
                "exit_reasons": {},
            }
        )
        return base

    gross = float(sum(t.gross_pnl for t in trades))
    comm = float(sum(t.commission for t in trades))
    slip = float(sum(getattr(t, "slippage_cost", 0.0) or 0.0 for t in trades))
    holds = [(t.exit_time - t.entry_time).total_seconds() / 60.0 for t in trades]
    contracts = [t.contracts for t in trades]
    same_bar = sum(
        1
        for i in range(len(trades) - 1)
        if trades[i + 1].entry_time == trades[i].exit_time
    )
    base.update(
        {
            "total_gross_pnl": round(gross, 2),
            "total_commission": round(comm, 2),
            "total_slippage": round(slip, 2),
            "avg_hold_minutes": round(float(np.mean(holds)), 2),
            "median_hold_minutes": round(float(np.median(holds)), 2),
            "avg_contracts": round(float(np.mean(contracts)), 3),
            "max_contracts": int(max(contracts)),
            "same_bar_reentries": int(same_bar),
            "exit_reasons": dict(Counter(t.exit_reason for t in trades)),
        }
    )
    return base


def _run_one(df: pd.DataFrame, strategy_name: str, phase: str, tag: str) -> Dict[str, Any]:
    strategy = _strategy(strategy_name, phase)
    kwargs = _engine_kwargs(phase)
    result = run_backtest(
        df=df,
        strategy=strategy,
        symbol="MNQ",
        timeframe="5m",
        account_size=ACCOUNT,
        risk_pct=RISK_PCT,
        **kwargs,
    )
    metrics = _extra_metrics(result, ACCOUNT)
    metrics["split"] = tag
    metrics["phase"] = phase
    metrics["bars"] = int(len(df))
    if len(df):
        metrics["start"] = str(df.index[0])
        metrics["end"] = str(df.index[-1])
    return metrics


def _walk_forward(df: pd.DataFrame, strategy_name: str, phase: str) -> Dict[str, Any]:
    kwargs = _engine_kwargs(phase)

    def _bt(train_or_test_df, strat):
        return run_backtest(
            df=train_or_test_df,
            strategy=strat,
            symbol="MNQ",
            timeframe="5m",
            account_size=ACCOUNT,
            risk_pct=RISK_PCT,
            **kwargs,
        )

    # Monkeypatch-free: walk_forward_search calls run_backtest with the
    # historical signature. If the engine accepts **kwargs via defaults we
    # wrap by temporarily replacing run_backtest in the walk_forward module.
    import src.backtest.walk_forward as wf

    orig = wf.run_backtest

    def _wrapped(df, strategy, symbol, timeframe, account_size, risk_pct, **_ignored):
        return _bt(df, strategy)

    wf.run_backtest = _wrapped  # type: ignore
    try:
        folds = walk_forward_search(
            df=df,
            strategy_cls=STRATEGY_CLASSES[strategy_name],
            param_grid=_strategy_ctor_kwargs(strategy_name, phase),
            symbol="MNQ",
            timeframe="5m",
            account_size=ACCOUNT,
            risk_pct=RISK_PCT,
            train_days=WF_TRAIN_DAYS,
            test_days=WF_TEST_DAYS,
        )
        oos = aggregate_oos(folds)
        fold_dump = [
            {
                "fold": f.fold,
                "train_start": str(f.train_start),
                "train_end": str(f.train_end),
                "test_start": str(f.test_start),
                "test_end": str(f.test_end),
                "train_metrics": {
                    k: f.train_metrics.get(k)
                    for k in (
                        "trade_count",
                        "win_rate",
                        "profit_factor",
                        "expectancy",
                        "total_pnl",
                        "max_drawdown",
                        "sharpe",
                    )
                },
                "test_metrics": {
                    k: f.test_metrics.get(k)
                    for k in (
                        "trade_count",
                        "win_rate",
                        "profit_factor",
                        "expectancy",
                        "total_pnl",
                        "max_drawdown",
                        "sharpe",
                    )
                },
            }
            for f in folds
        ]
        # Average in-sample (train) vs OOS (test) PnL for the sprint table.
        train_pnls = [f.train_metrics["total_pnl"] for f in folds]
        test_pnls = [f.test_metrics["total_pnl"] for f in folds]
        return {
            "symbol": "MNQ",
            "strategy": strategy_name,
            "phase": phase,
            "oos_summary": oos,
            "avg_is_pnl_per_fold": round(float(np.mean(train_pnls)), 2) if train_pnls else None,
            "avg_oos_pnl_per_fold": round(float(np.mean(test_pnls)), 2) if test_pnls else None,
            "folds": fold_dump,
        }
    finally:
        wf.run_backtest = orig  # type: ignore


def _write(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str))
    print(f"wrote {path}")


def run_phase(phase: str) -> Dict[str, Any]:
    df = load_ohlcv("MNQ", "5m")
    cut = pd.Timestamp(HOLDOUT_OOS_START, tz=df.index.tz)
    is_df = df[df.index < cut]
    oos_df = df[df.index >= cut]

    out_dir = SPRINT_DIR / phase
    summary: Dict[str, Any] = {
        "phase": phase,
        "symbol": "MNQ",
        "timeframe": "5m",
        "account_size": ACCOUNT,
        "risk_pct": RISK_PCT,
        "holdout_oos_start": HOLDOUT_OOS_START,
        "engine_kwargs": _engine_kwargs(phase),
        "disclaimer": (
            "Paper/backtest only. Metrics are historical simulations with "
            "modeled costs, not live results, and do not imply future profit."
        ),
        "strategies": {},
    }

    for name in STRATEGIES:
        print(f"=== {phase} / {name} ===", flush=True)
        full = _run_one(df, name, phase, "full")
        ins = _run_one(is_df, name, phase, "in_sample")
        oos = _run_one(oos_df, name, phase, "holdout_oos")
        print(f"  full pnl={full['total_pnl']} trades={full['trade_count']}", flush=True)
        print(f"  IS   pnl={ins['total_pnl']} trades={ins['trade_count']}", flush=True)
        print(f"  OOS  pnl={oos['total_pnl']} trades={oos['trade_count']}", flush=True)
        wf = _walk_forward(df, name, phase)
        print(f"  WF OOS {wf['oos_summary']}", flush=True)
        block = {"full": full, "in_sample": ins, "holdout_oos": oos, "walk_forward": wf}
        summary["strategies"][name] = block
        _write(out_dir / f"MNQ_5m_{name}.json", block)

    _write(out_dir / "summary.json", summary)
    return summary


def _row(metrics: Dict[str, Any]) -> str:
    def fmt(key, width=10):
        v = metrics.get(key)
        if v is None:
            return f"{'n/a':>{width}}"
        if isinstance(v, float):
            return f"{v:>{width}.2f}"
        return f"{v:>{width}}"

    return (
        f"{fmt('trade_count', 8)} {fmt('win_rate', 8)} {fmt('profit_factor', 8)} "
        f"{fmt('expectancy', 10)} {fmt('total_pnl', 12)} {fmt('max_drawdown', 12)} "
        f"{fmt('total_commission', 10)} {fmt('same_bar_reentries', 8)}"
    )


def compare() -> str:
    before_path = SPRINT_DIR / "before" / "summary.json"
    after_path = SPRINT_DIR / "after" / "summary.json"
    before = json.loads(before_path.read_text())
    after = json.loads(after_path.read_text())
    header = (
        f"{'split':<14} {'strat':<16} {'trades':>8} {'win%':>8} {'PF':>8} "
        f"{'E[$]':>10} {'pnl':>12} {'maxDD':>12} {'comm':>10} {'sameBar':>8}"
    )
    lines = [
        "# Sprint 1 before/after (MNQ 5m)",
        "",
        "Paper/backtest only. Not live trading. No guaranteed profit.",
        "",
        f"Holdout OOS start (locked): `{HOLDOUT_OOS_START}`",
        "",
        header,
        "-" * len(header),
    ]
    for split in ("full", "in_sample", "holdout_oos"):
        for name in STRATEGIES:
            for label, blob in (("before", before), ("after", after)):
                m = blob["strategies"][name][split]
                lines.append(f"{split:<14} {name+'/'+label:<16} {_row(m)}")
        lines.append("")

    lines += ["## Walk-forward OOS (180d/60d, concatenated test folds)", ""]
    lines.append(
        f"{'strat':<16} {'phase':<8} {'folds':>6} {'oos_trades':>10} "
        f"{'oos_pnl':>12} {'avg_IS_pnl':>12} {'avg_OOS_pnl':>12} {'t_stat':>8} {'sig':>6}"
    )
    for name in STRATEGIES:
        for label, blob in (("before", before), ("after", after)):
            wf = blob["strategies"][name]["walk_forward"]
            o = wf["oos_summary"]
            lines.append(
                f"{name:<16} {label:<8} {o.get('folds', 0):>6} {o.get('total_oos_trades', 0):>10} "
                f"{o.get('total_oos_pnl', 0):>12} {wf.get('avg_is_pnl_per_fold'):>12} "
                f"{wf.get('avg_oos_pnl_per_fold'):>12} {o.get('t_stat'):>8} {o.get('significant'):>6}"
            )
    text = "\n".join(lines) + "\n"
    (SPRINT_DIR / "compare.md").write_text(text)
    print(text)
    return text


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--phase", choices=["before", "after", "compare", "all"], default="all")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    SPRINT_DIR.mkdir(parents=True, exist_ok=True)
    if args.phase in ("before", "all"):
        run_phase("before")
    if args.phase in ("after", "all"):
        run_phase("after")
    if args.phase in ("compare", "all"):
        if (SPRINT_DIR / "before" / "summary.json").exists() and (
            SPRINT_DIR / "after" / "summary.json"
        ).exists():
            compare()
        else:
            print("compare skipped: need reports/sprint1/before and after summaries")


if __name__ == "__main__":
    main()
