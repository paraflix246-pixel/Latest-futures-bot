#!/usr/bin/env python
"""
Harden a locked candidate on the official sprint-1 engine.

  - Walk-forward 180/60 + locked holdout (same gate as research_cycle).
  - One-factor ±20% param sensitivity (does nearby still pass?).
  - Leave-one-regime-out on discovery trades (quarter / ATR tercile / trend).

Paper / backtest only. Never uses holdout to pick params. No live trading.

Usage:
    python scripts/harden_candidate.py --family filtered_orb_2 --symbol MES
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import REPORTS_DIR  # noqa: E402
from scripts.research_cycle import (  # noqa: E402
    FAMILIES,
    _locked_params,
    _t_from_trades,
    run_holdout,
    symbol_gate,
)
from src.backtest.engine import run_backtest  # noqa: E402
from src.backtest.walk_forward import _t_stat, aggregate_oos, walk_forward_search  # noqa: E402
from src.data.loader import load_ohlcv  # noqa: E402
from src.research.presets import (  # noqa: E402
    ACCOUNT_SIZE,
    HOLDOUT_OOS_START,
    RISK_PCT,
    SPRINT1_AFTER_ENGINE,
    WF_TEST_DAYS,
    WF_TRAIN_DAYS,
)
from src.strategies.indicators import atr  # noqa: E402
from src.strategies.session import session_clock  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--family", default="filtered_orb_2")
    p.add_argument("--symbol", default="MES")
    p.add_argument("--timeframe", default="5m")
    return p.parse_args()


def _wf(df, cls, grid, symbol, timeframe, train_days=WF_TRAIN_DAYS, test_days=WF_TEST_DAYS):
    folds = walk_forward_search(
        df=df,
        strategy_cls=cls,
        param_grid=grid,
        symbol=symbol,
        timeframe=timeframe,
        account_size=ACCOUNT_SIZE,
        risk_pct=RISK_PCT,
        train_days=train_days,
        test_days=test_days,
        engine_kwargs=SPRINT1_AFTER_ENGINE,
    )
    return folds, aggregate_oos(folds)


def _perturb(base: dict) -> List[Dict[str, Any]]:
    """One-factor ±20% around numeric hunt params. Booleans stay locked."""
    rows = [{"label": "locked", **base}]
    for key, val in base.items():
        if isinstance(val, bool) or val is None:
            continue
        if isinstance(val, int) and not isinstance(val, bool):
            lo = max(1, int(round(val * 0.8)))
            hi = int(round(val * 1.2))
            if lo != val:
                rows.append({"label": f"{key}={lo}", **{**base, key: lo}})
            if hi != val:
                rows.append({"label": f"{key}={hi}", **{**base, key: hi}})
        elif isinstance(val, float):
            lo = round(val * 0.8, 4)
            hi = round(val * 1.2, 4)
            if lo != val:
                rows.append({"label": f"{key}={lo}", **{**base, key: lo}})
            if hi != val:
                rows.append({"label": f"{key}={hi}", **{**base, key: hi}})
    # de-dupe by param tuple
    seen = set()
    out = []
    for r in rows:
        key = tuple(sorted((k, v) for k, v in r.items() if k != "label"))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out


def _loro(df: pd.DataFrame, trades) -> Dict[str, Any]:
    if not trades:
        return {}
    minutes, dates = session_clock(df.index)
    daily = df.resample("1D").agg({"high": "max", "low": "min", "close": "last"}).dropna()
    daily_atr = atr(daily["high"], daily["low"], daily["close"], 14).shift(1)
    sma20 = daily["close"].rolling(20).mean().shift(1)

    recs = []
    for t in trades:
        local = t.entry_time.tz_convert("America/New_York")
        d = local.date()
        ts = pd.Timestamp(d)
        a = daily_atr.get(ts, np.nan) if ts in daily_atr.index else np.nan
        recs.append(
            {
                "pnl": t.pnl,
                "quarter": f"{local.year}Q{((local.month - 1) // 3) + 1}",
                "atr": float(a) if a == a else np.nan,
                "trend": (
                    "up"
                    if ts in sma20.index and daily["close"].get(ts, np.nan) > sma20.get(ts, np.nan)
                    else "down"
                ),
            }
        )
    frame = pd.DataFrame(recs)
    if frame["atr"].notna().sum() >= 6:
        try:
            frame["atr_tercile"] = pd.qcut(frame["atr"], 3, labels=["low", "mid", "high"], duplicates="drop")
        except ValueError:
            frame["atr_tercile"] = "na"
    else:
        frame["atr_tercile"] = "na"

    out: Dict[str, Any] = {}
    for col in ("quarter", "atr_tercile", "trend"):
        groups = {}
        for regime, part in frame.groupby(col, observed=False):
            left = frame[frame[col] != regime]
            tstat = _t_stat(left["pnl"].tolist()) if len(left) else None
            groups[str(regime)] = {
                "left_out_n": int(len(part)),
                "left_out_pnl": round(float(part["pnl"].sum()), 2),
                "remaining_n": int(len(left)),
                "remaining_t": round(tstat, 3) if tstat is not None else None,
            }
        out[col] = groups
    return out


def main() -> None:
    args = parse_args()
    cls, grid, kind = FAMILIES[args.family]
    locked = _locked_params(grid)
    df = load_ohlcv(args.symbol, args.timeframe)
    cut = pd.Timestamp(HOLDOUT_OOS_START, tz=df.index.tz)
    discovery = df[df.index < cut]
    holdout = df[df.index >= cut]
    out_dir = ROOT / REPORTS_DIR / "cycles" / "harden" / f"{args.symbol}_{args.family}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== harden {args.symbol} {args.family} locked={locked} ===", flush=True)
    print(f"tape {df.index[0]} -> {df.index[-1]} n={len(df)} discovery={len(discovery)}", flush=True)

    folds, oos = _wf(discovery, cls, {k: [v] for k, v in locked.items()}, args.symbol, args.timeframe)
    ho = run_holdout(holdout, cls, args.symbol, args.timeframe, params=locked)
    ok, why = symbol_gate(oos, ho)
    gate = f"PASS_{args.symbol}" if ok else why
    print(f"  official WF {oos}", flush=True)
    print(f"  holdout t={ho.get('t_stat')} n={ho.get('trade_count')} pnl={ho.get('total_pnl')} held_past={ho.get('held_past_rth_close')}", flush=True)
    print(f"  gate {gate}", flush=True)

    # Longer-fold diagnostic (not the pass gate): 90/30 → more OOS trades.
    folds_90, oos_90 = _wf(discovery, cls, {k: [v] for k, v in locked.items()}, args.symbol, args.timeframe, 90, 30)
    print(f"  diagnostic 90/30 WF {oos_90}", flush=True)

    disc_res = run_backtest(
        discovery, cls(**locked), args.symbol, args.timeframe, ACCOUNT_SIZE, RISK_PCT, **SPRINT1_AFTER_ENGINE
    )
    loro = _loro(discovery, disc_res.trades)
    print(f"  discovery n={len(disc_res.trades)} t={_t_from_trades(disc_res.trades)} LORO keys={list(loro)}", flush=True)

    sensitivity = []
    for row in _perturb(locked):
        label = row.pop("label")
        params = row
        g = {k: [v] for k, v in params.items()}
        print(f"  -- sensitivity {label} {params}", flush=True)
        _, soos = _wf(discovery, cls, g, args.symbol, args.timeframe)
        sho = run_holdout(holdout, cls, args.symbol, args.timeframe, params=params)
        sok, swhy = symbol_gate(soos, sho)
        sensitivity.append(
            {
                "label": label,
                "params": params,
                "wf": soos,
                "holdout_t": sho.get("t_stat"),
                "holdout_n": sho.get("trade_count"),
                "holdout_pnl": sho.get("total_pnl"),
                "gate": f"PASS_{args.symbol}" if sok else swhy,
            }
        )
        print(f"     WF t={soos.get('t_stat')} n={soos.get('total_oos_trades')} HO t={sho.get('t_stat')} n={sho.get('trade_count')} -> {sensitivity[-1]['gate']}", flush=True)

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "family": args.family,
        "kind": kind,
        "symbol": args.symbol,
        "locked_params": locked,
        "tape": {"rows": int(len(df)), "start": str(df.index[0]), "end": str(df.index[-1])},
        "official_wf": oos,
        "official_holdout": ho,
        "gate": gate,
        "diagnostic_wf_90_30": oos_90,
        "discovery_n": len(disc_res.trades),
        "discovery_t": _t_from_trades(disc_res.trades),
        "leave_one_regime_out": loro,
        "sensitivity": sensitivity,
        "engine": SPRINT1_AFTER_ENGINE,
        "note": "Holdout n is thin if <30; sensitivity/LORO are diagnostics, not a second holdout pick. Paper only.",
    }
    (out_dir / "harden.json").write_text(json.dumps(payload, indent=2, default=str))

    lines = [
        f"# Harden {args.symbol} `{args.family}`",
        "",
        "Paper / backtest only. Sprint-1 fills. No live trading.",
        "",
        f"Locked params: `{locked}`",
        "",
        f"- Official WF 180/60: n={oos.get('total_oos_trades')} t={oos.get('t_stat')} pnl={oos.get('total_oos_pnl')}",
        f"- Holdout from {HOLDOUT_OOS_START}: n={ho.get('trade_count')} t={ho.get('t_stat')} pnl={ho.get('total_pnl')} overnight={ho.get('held_past_rth_close')}",
        f"- Gate: **{gate}**",
        f"- Diagnostic WF 90/30 (not the gate): n={oos_90.get('total_oos_trades')} t={oos_90.get('t_stat')}",
        "",
        "## Sensitivity (±20% one-factor)",
        "",
        "| Variant | WF n | WF t | HO n | HO t | Gate |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for s in sensitivity:
        lines.append(
            f"| {s['label']} | {s['wf'].get('total_oos_trades')} | {s['wf'].get('t_stat')} | {s['holdout_n']} | {s['holdout_t']} | {s['gate']} |"
        )
    lines.extend(["", "## Leave-one-regime-out (discovery trades)", ""])
    for col, groups in loro.items():
        lines.append(f"### {col}")
        lines.append("")
        lines.append("| Left out | n left out | remaining n | remaining t |")
        lines.append("|---|---:|---:|---:|")
        for regime, g in groups.items():
            lines.append(f"| {regime} | {g['left_out_n']} | {g['remaining_n']} | {g['remaining_t']} |")
        lines.append("")
    lines.append("PASS_MES on thin holdout stays **provisional** until holdout n is healthier or nearby params also pass.")
    (out_dir / "SUMMARY.md").write_text("\n".join(lines))
    print(f"Wrote {out_dir}", flush=True)


if __name__ == "__main__":
    main()
