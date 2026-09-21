#!/usr/bin/env python
"""
Walk-forward + locked-holdout evaluation for the RTH session strategies.

Protocol (matches prior research sprints):
  1. Split each symbol 80/20 by time. The last 20% is locked and is not
     used to pick parameters.
  2. Walk-forward search on the discovery slice only (train 180d / test 60d).
  3. Holdout is run exactly once with each strategy's pre-registered
     constructor defaults — not the walk-forward winners.
  4. Kill rule: walk-forward OOS t-stat < 2, or MES fails to replicate
     (MES OOS t < 2). No live trading. No edge claims from in-sample fit.

Usage:
    python scripts/eval_new_strategies.py
    python scripts/eval_new_strategies.py --symbol MNQ --strategy impulse_clock
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DEFAULT_ACCOUNT_SIZE, DEFAULT_RISK_PCT, DEFAULT_TIMEFRAME  # noqa: E402
from src.backtest.engine import run_backtest  # noqa: E402
from src.backtest.metrics import compute_metrics  # noqa: E402
from src.backtest.walk_forward import SIGNIFICANCE_MIN_T_STAT, aggregate_oos, walk_forward_search  # noqa: E402
from src.data.loader import load_ohlcv  # noqa: E402
from src.strategies.impulse_clock import ImpulseClockStrategy  # noqa: E402
from src.strategies.orb_break_fade import OrbBreakFadeStrategy  # noqa: E402
from src.strategies.vol_squeeze_expansion import VolSqueezeExpansionStrategy  # noqa: E402

DISCOVERY_FRAC = 0.80
TRAIN_DAYS = 180
TEST_DAYS = 60
SYMBOLS = ["MNQ", "MES"]
NEW_STRATEGIES = {
    "orb_break_fade": (OrbBreakFadeStrategy, {
        "or_minutes": [15, 30], "failure_bars": [3, 5],
    }),
    "vol_squeeze_expansion": (VolSqueezeExpansionStrategy, {
        "squeeze_percentile": [15, 25], "volume_mult": [1.2, 1.5],
    }),
    "impulse_clock": (ImpulseClockStrategy, {
        "impulse_atr_mult": [1.5, 2.0], "max_hold_bars": [6, 12],
    }),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", nargs="+", default=SYMBOLS, choices=SYMBOLS)
    parser.add_argument("--strategy", nargs="+", default=list(NEW_STRATEGIES),
                        choices=list(NEW_STRATEGIES) + ["all"])
    parser.add_argument("--timeframe", default=DEFAULT_TIMEFRAME)
    parser.add_argument("--account-size", type=float, default=DEFAULT_ACCOUNT_SIZE)
    parser.add_argument("--risk-pct", type=float, default=DEFAULT_RISK_PCT)
    return parser.parse_args()


def split_discovery_holdout(df):
    split_pos = int(len(df) * DISCOVERY_FRAC)
    split_ts = df.index[split_pos]
    return df.iloc[:split_pos], df.iloc[split_pos:], split_ts


def _exit_counts(trades):
    return dict(Counter(t.exit_reason for t in trades))


def _t_from_trades(trades):
    from src.backtest.walk_forward import _t_stat
    return _t_stat([t.pnl for t in trades])


def run_holdout(df, strategy_cls, symbol, timeframe, account_size, risk_pct):
    strat = strategy_cls()  # locked constructor defaults
    result = run_backtest(df, strat, symbol, timeframe, account_size, risk_pct)
    metrics = compute_metrics(result, account_size)
    t_stat = _t_from_trades(result.trades)
    metrics["t_stat"] = round(t_stat, 3) if t_stat is not None else None
    metrics["exit_reasons"] = _exit_counts(result.trades)
    overnight = 0
    for t in result.trades:
        local_exit = t.exit_time.tz_convert("America/New_York")
        if local_exit.hour > 16 or (local_exit.hour == 16 and local_exit.minute > 5):
            overnight += 1
    metrics["held_past_rth_close"] = overnight
    return metrics


def verdict(wf_oos: dict, holdout: dict, mes_oos: dict | None) -> str:
    wf_t = wf_oos.get("t_stat")
    if wf_t is None or wf_t < SIGNIFICANCE_MIN_T_STAT or not wf_oos.get("significant"):
        return "KILLED (walk-forward OOS t<2 or not significant)"
    if mes_oos is not None:
        mes_t = mes_oos.get("t_stat")
        if mes_t is None or mes_t < SIGNIFICANCE_MIN_T_STAT or not mes_oos.get("significant"):
            return "KILLED (MES replication failed)"
    hold_t = holdout.get("t_stat")
    if hold_t is None or hold_t < SIGNIFICANCE_MIN_T_STAT:
        return "KILLED (locked holdout t<2)"
    return "SURVIVED (WF + holdout + MES) — still not a live-trading claim"


def write_summary(reports_dir: Path, rows: list[dict]) -> None:
    lines = [
        "# New RTH session strategies — evaluation",
        "",
        "Paper / backtest only. Fills: sprint-1 engine (signal-bar close + 1 tick, "
        "stop/target on subsequent bars). Clock exits: `time_stop` / `rth_flatten` "
        "at close ± 1 tick. Kill rule: walk-forward OOS t < 2 **or** MES fails to replicate.",
        "",
        "Holdout uses **pre-registered constructor defaults**, not walk-forward winners.",
        "",
        "| Symbol | Strategy | WF folds | WF OOS n | WF OOS PnL | WF t | WF sig | Holdout n | Holdout PnL | Holdout t | Verdict |",
        "|---|---|---:|---:|---:|---:|---|---:|---:|---:|---|",
    ]
    for r in rows:
        wf = r["walk_forward_oos"]
        ho = r["holdout"]
        lines.append(
            "| {symbol} | {strategy} | {folds} | {wf_n} | {wf_pnl} | {wf_t} | {wf_sig} | {ho_n} | {ho_pnl} | {ho_t} | {verdict} |".format(
                symbol=r["symbol"],
                strategy=r["strategy"],
                folds=wf.get("folds", 0),
                wf_n=wf.get("total_oos_trades", 0),
                wf_pnl=wf.get("total_oos_pnl", 0),
                wf_t=wf.get("t_stat"),
                wf_sig=wf.get("significant"),
                ho_n=ho.get("trade_count", 0),
                ho_pnl=ho.get("total_pnl", 0),
                ho_t=ho.get("t_stat"),
                verdict=r["verdict"],
            )
        )
    lines.extend(["", "No strategy is claimed to be profitable in live trading.", ""])
    (reports_dir / "SUMMARY.md").write_text("\n".join(lines))


def main() -> None:
    args = parse_args()
    strategies = list(NEW_STRATEGIES) if "all" in args.strategy else args.strategy
    reports_dir = Path(__file__).resolve().parent.parent / "reports" / "new_strategies"
    reports_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    wf_by_key = {}

    for symbol in args.symbol:
        df = load_ohlcv(symbol, args.timeframe)
        discovery, holdout, split_ts = split_discovery_holdout(df)
        print(f"\n=== {symbol} {args.timeframe} split={split_ts} "
              f"discovery={len(discovery)} holdout={len(holdout)} ===", flush=True)

        for name in strategies:
            cls, grid = NEW_STRATEGIES[name]
            print(f"\n-- {symbol} / {name} walk-forward --", flush=True)
            folds = walk_forward_search(
                df=discovery, strategy_cls=cls, param_grid=grid,
                symbol=symbol, timeframe=args.timeframe,
                account_size=args.account_size, risk_pct=args.risk_pct,
                train_days=TRAIN_DAYS, test_days=TEST_DAYS,
            )
            oos = aggregate_oos(folds)
            print(f"  WF OOS: {json.dumps(oos)}", flush=True)

            print(f"-- {symbol} / {name} locked holdout (defaults) --", flush=True)
            hold_metrics = run_holdout(
                holdout, cls, symbol, args.timeframe, args.account_size, args.risk_pct,
            )
            print(f"  Holdout: {json.dumps(hold_metrics)}", flush=True)

            payload = {
                "symbol": symbol,
                "strategy": name,
                "split": str(split_ts),
                "protocol": {
                    "discovery_frac": DISCOVERY_FRAC,
                    "train_days": TRAIN_DAYS,
                    "test_days": TEST_DAYS,
                    "holdout_params": "constructor_defaults",
                    "fills": "sprint1_close_plus_1tick",
                    "paper_only": True,
                },
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
                "holdout": hold_metrics,
            }
            wf_by_key[(symbol, name)] = payload
            (reports_dir / f"{symbol}_{name}.json").write_text(json.dumps(payload, indent=2))

    for symbol in args.symbol:
        for name in strategies:
            payload = wf_by_key[(symbol, name)]
            mes = wf_by_key.get(("MES", name), {}).get("walk_forward_oos") if symbol == "MNQ" else None
            payload["verdict"] = verdict(payload["walk_forward_oos"], payload["holdout"], mes)
            (reports_dir / f"{symbol}_{name}.json").write_text(json.dumps(payload, indent=2))
            rows.append(payload)

    rows.sort(key=lambda r: (r["strategy"], r["symbol"]))
    (reports_dir / "leaderboard.json").write_text(json.dumps([
        {
            "symbol": r["symbol"],
            "strategy": r["strategy"],
            "verdict": r["verdict"],
            **r["walk_forward_oos"],
            "holdout_t": r["holdout"].get("t_stat"),
            "holdout_pnl": r["holdout"].get("total_pnl"),
            "holdout_trades": r["holdout"].get("trade_count"),
        }
        for r in rows
    ], indent=2))
    write_summary(reports_dir, rows)
    print("\n=== VERDICTS ===")
    for r in rows:
        print(f"{r['symbol']:4} {r['strategy']:24} {r['verdict']}")
    print(f"\nWrote {reports_dir}")


if __name__ == "__main__":
    main()
