#!/usr/bin/env python
"""
Sprint 2 improve-loop: MES replication already on disk; this runs MNQ
walk-forward of a priori risk/cost filters (selection on WF only), then
confirms the best non-baseline (if it beats sprint-1 after t-stat) on
MES WF + MNQ locked holdout.

Paper/backtest only. No live trading. No profit claim.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.run_sprint import (  # noqa: E402
    ACCOUNT,
    HOLDOUT_OOS_START,
    RISK_PCT,
    WF_TEST_DAYS,
    WF_TRAIN_DAYS,
    _extra_metrics,
)
from src.backtest.engine import run_backtest  # noqa: E402
from src.backtest.walk_forward import aggregate_oos, walk_forward_search  # noqa: E402
from src.data.loader import load_ohlcv  # noqa: E402
from src.strategies.ensemble import EnsembleStrategy  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / "reports" / "sprint2"

BASE_ENGINE = dict(
    fill_model="next_open",
    apply_exit_slippage=True,
    gap_aware_stops=True,
    trail_update="next_bar",
    cooldown_bars=3,
    allow_same_bar_reentry=False,
    daily_loss_halt_pct=2.0,
    flatten_at_rth_close=True,
    max_contracts=10,
)
STRAT_KW = dict(rth_only=True, breakout_in_range=False, event_trigger=True)

VARIANTS = {
    "s1_after_baseline": {},
    "min_atr_gate": {"min_atr_gate": True},
    "cost_frac_0.25": {"max_cost_frac_of_risk": 0.25},
    "skip_open_30m": {"skip_rth_open_minutes": 30},
    "cooldown_6": {"cooldown_bars": 6},
    "halt_1pct": {"daily_loss_halt_pct": 1.0},
    "max_contracts_5": {"max_contracts": 5},
    "atr_plus_cost": {"min_atr_gate": True, "max_cost_frac_of_risk": 0.25},
}


def _engine(extra: dict) -> dict:
    kw = dict(BASE_ENGINE)
    kw.update(extra)
    return kw


def _wrap(symbol: str, extra: dict):
    import src.backtest.walk_forward as wf

    orig = wf.run_backtest
    eng = _engine(extra)

    def _bt(df, strategy, symbol_, timeframe, account_size, risk_pct, **_):
        return run_backtest(df, strategy, symbol, timeframe, account_size, risk_pct, **eng)

    wf.run_backtest = _bt  # type: ignore
    return orig, wf


def walk_forward(df, symbol: str, extra: dict) -> dict:
    orig, wf = _wrap(symbol, extra)
    try:
        folds = walk_forward_search(
            df,
            EnsembleStrategy,
            {k: [v] for k, v in STRAT_KW.items()},
            symbol,
            "5m",
            ACCOUNT,
            RISK_PCT,
            WF_TRAIN_DAYS,
            WF_TEST_DAYS,
        )
        oos = aggregate_oos(folds)
        oos["avg_is_pnl"] = round(float(np.mean([f.train_metrics["total_pnl"] for f in folds])), 2) if folds else None
        return oos
    finally:
        wf.run_backtest = orig  # type: ignore


def split_run(df, symbol: str, extra: dict) -> dict:
    cut = pd.Timestamp(HOLDOUT_OOS_START, tz=df.index.tz)
    eng = _engine(extra)
    out = {}
    for tag, d in (
        ("full", df),
        ("in_sample", df[df.index < cut]),
        ("holdout_oos", df[df.index >= cut]),
    ):
        res = run_backtest(
            d, EnsembleStrategy(**STRAT_KW), symbol, "5m", ACCOUNT, RISK_PCT, **eng
        )
        m = _extra_metrics(res, ACCOUNT)
        out[tag] = {
            k: m[k]
            for k in (
                "trade_count",
                "win_rate",
                "profit_factor",
                "expectancy",
                "total_pnl",
                "max_drawdown",
                "total_commission",
                "total_slippage",
            )
        }
    return out


def time_of_day(df: pd.DataFrame) -> dict:
    cut = pd.Timestamp(HOLDOUT_OOS_START, tz=df.index.tz)
    is_df = df[df.index < cut]
    res = run_backtest(
        is_df, EnsembleStrategy(**STRAT_KW), "MNQ", "5m", ACCOUNT, RISK_PCT, **BASE_ENGINE
    )
    from src.backtest.walk_forward import _t_stat

    rows = []
    if not res.trades:
        return {"hours": []}
    et = pd.DatetimeIndex([t.entry_time for t in res.trades]).tz_convert("America/New_York")
    hours = et.hour
    pnls = np.array([t.pnl for t in res.trades])
    for h in range(24):
        mask = hours == h
        n = int(mask.sum())
        if n < 5:
            continue
        bucket = pnls[mask]
        tstat = _t_stat(bucket.tolist())
        rows.append(
            {
                "hour_et": h,
                "trades": n,
                "pnl": round(float(bucket.sum()), 2),
                "expectancy": round(float(bucket.mean()), 2),
                "t_stat": round(tstat, 3) if tstat is not None else None,
            }
        )
    rows.sort(key=lambda r: (r["t_stat"] is not None, r["t_stat"] or -999), reverse=True)
    return {"hours": rows, "note": "In-sample only. Do not promote a bucket unless t>=2 and n>=30."}


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    mnq = load_ohlcv("MNQ", "5m")
    leaderboard = []
    print("=== MNQ walk-forward filter/risk variants ===", flush=True)
    for name, extra in VARIANTS.items():
        print(f"  {name}...", flush=True)
        oos = walk_forward(mnq, "MNQ", extra)
        print(f"    {oos}", flush=True)
        leaderboard.append({"variant": name, "extra": extra, **oos})
    leaderboard.sort(key=lambda r: (r.get("t_stat") is not None, r.get("t_stat") or -999), reverse=True)
    (OUT / "MNQ_filter_wf_leaderboard.json").write_text(json.dumps(leaderboard, indent=2))

    baseline_t = next(r["t_stat"] for r in leaderboard if r["variant"] == "s1_after_baseline")
    best = leaderboard[0]
    print(f"Best WF t={best['t_stat']} ({best['variant']}); baseline t={baseline_t}", flush=True)

    confirms = {}
    if best["variant"] != "s1_after_baseline" and (best.get("t_stat") or -999) > (baseline_t or -999):
        print("Confirming best on MNQ splits + MES WF (holdout not used for selection)", flush=True)
        confirms["mnq_splits"] = split_run(mnq, "MNQ", best["extra"])
        mes = load_ohlcv("MES", "5m")
        confirms["mes_wf"] = walk_forward(mes, "MES", best["extra"])
        confirms["mes_splits"] = split_run(mes, "MES", best["extra"])
        print("  MNQ splits", confirms["mnq_splits"])
        print("  MES WF", confirms["mes_wf"])
    else:
        print("No WF t-stat improvement over sprint-1 after; not promoting a filter.", flush=True)

    tod = time_of_day(mnq)
    print("TOD (IS)", tod["hours"][:8], flush=True)
    (OUT / "MNQ_time_of_day_is.json").write_text(json.dumps(tod, indent=2))
    (OUT / "filter_confirm.json").write_text(json.dumps(confirms, indent=2, default=str))
    print("wrote", OUT)


if __name__ == "__main__":
    main()
