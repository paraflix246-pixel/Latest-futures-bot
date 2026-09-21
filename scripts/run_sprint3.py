#!/usr/bin/env python
"""
Sprint 3 — new hypothesis, not a 5m ensemble retune.

Pre-registered claim:
  On 15-minute and 1-hour bars (resampled from 5m), a *single* RTH-only
  strategy (trend-following OR mean-reversion — not an ensemble) with the
  sprint-1 realistic fill/risk overlay has walk-forward OOS t-stat >= 2
  on MNQ and the same sign on MES.

No EMA/Donchian/ADX grid. Event-trigger + next-open fills + flatten at
the cash close + 2% daily halt + 10-contract cap.

Paper/backtest only. No live trading.

Usage:
    python scripts/run_sprint3.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DEFAULT_ACCOUNT_SIZE, DEFAULT_RISK_PCT, REPORTS_DIR  # noqa: E402
from src.backtest.engine import run_backtest  # noqa: E402
from src.backtest.metrics import compute_metrics  # noqa: E402
from src.backtest.walk_forward import aggregate_oos, walk_forward_search  # noqa: E402
from src.data.loader import load_ohlcv  # noqa: E402
from src.strategies.mean_reversion import MeanReversionStrategy  # noqa: E402
from src.strategies.trend_following import TrendFollowingStrategy  # noqa: E402

OUT = Path(__file__).resolve().parent.parent / REPORTS_DIR / "sprint3"
HOLDOUT_OOS_START = "2025-09-12"
ACCOUNT = DEFAULT_ACCOUNT_SIZE
RISK_PCT = DEFAULT_RISK_PCT
WF_TRAIN_DAYS = 180
WF_TEST_DAYS = 60

STRATEGIES = {
    "trend": (TrendFollowingStrategy, {}),
    "mean_reversion": (MeanReversionStrategy, {"event_trigger": True}),
}
TIMEFRAMES = ["15m", "1h"]
SYMBOLS = ["MNQ", "MES"]

# Hard risk overlay. Cooldown scales with bar size (~30–60 minutes).
ENGINE_BY_TF = {
    "15m": dict(
        fill_model="next_open",
        apply_exit_slippage=True,
        gap_aware_stops=True,
        trail_update="next_bar",
        cooldown_bars=2,
        allow_same_bar_reentry=False,
        daily_loss_halt_pct=2.0,
        flatten_at_rth_close=True,
        max_contracts=10,
        rth_entries_only=True,
    ),
    "1h": dict(
        fill_model="next_open",
        apply_exit_slippage=True,
        gap_aware_stops=True,
        trail_update="next_bar",
        cooldown_bars=1,
        allow_same_bar_reentry=False,
        daily_loss_halt_pct=2.0,
        flatten_at_rth_close=True,
        max_contracts=10,
        rth_entries_only=True,
    ),
}


def _wrap(symbol: str, timeframe: str):
    import src.backtest.walk_forward as wf

    orig = wf.run_backtest
    eng = ENGINE_BY_TF[timeframe]

    def _bt(df, strategy, symbol_, tf, account_size, risk_pct, **_):
        return run_backtest(df, strategy, symbol, timeframe, account_size, risk_pct, **eng)

    wf.run_backtest = _bt  # type: ignore
    return orig, wf


def _extra(result, account_size: float) -> dict:
    m = compute_metrics(result, account_size)
    trades = result.trades
    if not trades:
        m.update({"total_commission": 0.0, "total_slippage": 0.0})
        return m
    m["total_commission"] = round(float(sum(t.commission for t in trades)), 2)
    m["total_slippage"] = round(float(sum(getattr(t, "slippage_cost", 0.0) or 0.0 for t in trades)), 2)
    return m


def splits(df: pd.DataFrame, symbol: str, timeframe: str, strat) -> dict:
    cut = pd.Timestamp(HOLDOUT_OOS_START, tz=df.index.tz)
    eng = ENGINE_BY_TF[timeframe]
    out = {}
    for tag, d in (
        ("full", df),
        ("in_sample", df[df.index < cut]),
        ("holdout_oos", df[df.index >= cut]),
    ):
        res = run_backtest(d, strat, symbol, timeframe, ACCOUNT, RISK_PCT, **eng)
        m = _extra(res, ACCOUNT)
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


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    print(
        "Sprint 3 hypothesis: 15m/1h single-strategy RTH-only trend or "
        "mean-reversion, realistic fills, no ensemble.\n"
        "Paper/backtest only. Promising only if MNQ WF t>=2 AND MES WF PnL>0.\n",
        flush=True,
    )

    for symbol in SYMBOLS:
        for tf in TIMEFRAMES:
            df = load_ohlcv(symbol, tf)
            print(f"{symbol} {tf}: {len(df)} bars {df.index[0]} -> {df.index[-1]}", flush=True)
            for name, (cls, kwargs) in STRATEGIES.items():
                label = f"{symbol}_{tf}_{name}"
                print(f"  {label}...", flush=True)
                orig, wf = _wrap(symbol, tf)
                try:
                    folds = walk_forward_search(
                        df,
                        cls,
                        {k: [v] for k, v in kwargs.items()} if kwargs else {},
                        symbol,
                        tf,
                        ACCOUNT,
                        RISK_PCT,
                        WF_TRAIN_DAYS,
                        WF_TEST_DAYS,
                    )
                    oos = aggregate_oos(folds)
                finally:
                    wf.run_backtest = orig  # type: ignore

                strat = cls(**kwargs)
                sp = splits(df, symbol, tf, strat)
                row = {
                    "symbol": symbol,
                    "timeframe": tf,
                    "strategy": name,
                    "hypothesis": "single_rth_higher_tf",
                    "walk_forward": oos,
                    "splits": sp,
                    "promising": bool(
                        oos.get("t_stat") is not None
                        and oos["t_stat"] >= 2.0
                        and oos.get("total_oos_pnl", 0) > 0
                        and oos.get("total_oos_trades", 0) >= 30
                    ),
                    "disclaimer": "Paper/backtest only. Not live. Not a profit claim.",
                }
                rows.append(row)
                print(
                    f"    WF t={oos.get('t_stat')} pnl={oos.get('total_oos_pnl')} "
                    f"trades={oos.get('total_oos_trades')} holdout={sp['holdout_oos']['total_pnl']}",
                    flush=True,
                )
                (OUT / f"{label}.json").write_text(json.dumps(row, indent=2, default=str))

    # Replication: MNQ promising flag is WF-only; MES is the independent gate.
    summary_rows = []
    for r in rows:
        if r["symbol"] != "MNQ":
            continue
        mes = next(
            x
            for x in rows
            if x["symbol"] == "MES"
            and x["timeframe"] == r["timeframe"]
            and x["strategy"] == r["strategy"]
        )
        mnq_t = r["walk_forward"].get("t_stat")
        mes_pnl = mes["walk_forward"].get("total_oos_pnl", 0)
        mes_t = mes["walk_forward"].get("t_stat")
        replicated = bool(
            r["promising"] and mes_pnl > 0 and mes_t is not None and mes_t > 0
        )
        summary_rows.append(
            {
                "timeframe": r["timeframe"],
                "strategy": r["strategy"],
                "mnq_wf_t": mnq_t,
                "mnq_wf_pnl": r["walk_forward"].get("total_oos_pnl"),
                "mnq_wf_trades": r["walk_forward"].get("total_oos_trades"),
                "mnq_holdout_pnl": r["splits"]["holdout_oos"]["total_pnl"],
                "mes_wf_t": mes_t,
                "mes_wf_pnl": mes_pnl,
                "mes_holdout_pnl": mes["splits"]["holdout_oos"]["total_pnl"],
                "mnq_wf_clears_t2": r["promising"],
                "mes_replicates": replicated,
            }
        )

    payload = {
        "hypothesis": (
            "15m/1h single RTH-only trend or mean-reversion with realistic fills "
            "beats t>=2 on MNQ WF and replicates (positive t and PnL) on MES WF."
        ),
        "result": "no_validated_edge"
        if not any(s["mes_replicates"] for s in summary_rows)
        else "see_table",
        "disclaimer": "Paper/backtest only. Not live trading. No profit guarantee.",
        "table": summary_rows,
        "holdout_oos_start": HOLDOUT_OOS_START,
        "engine": ENGINE_BY_TF,
    }
    if not any(s["mes_replicates"] for s in summary_rows):
        payload["result"] = "no_validated_edge"
    (OUT / "summary.json").write_text(json.dumps(payload, indent=2, default=str))
    print("\n=== SPRINT 3 TABLE ===", flush=True)
    print(json.dumps(summary_rows, indent=2))
    print("wrote", OUT / "summary.json")


if __name__ == "__main__":
    main()
