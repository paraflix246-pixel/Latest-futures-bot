#!/usr/bin/env python
"""
Sprint 4 fill/slippage integrity audit.

Re-run the sprint-1 *after* MNQ 5m ensemble (the least-bad OHLCV result,
still not a validated edge) under harsher fills: 2–4 ticks/side, extra
ticks on gapped stops, 50% partial fills. Walk-forward + locked holdout.

Does not retune EMA/Donchian/ADX. Paper/backtest only.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

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

OUT = Path(__file__).resolve().parent.parent / "reports" / "sprint4"

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

STRESSES = {
    "ticks_1_baseline": {"slippage_ticks": 1},
    "ticks_2": {"slippage_ticks": 2},
    "ticks_3": {"slippage_ticks": 3},
    "ticks_4": {"slippage_ticks": 4},
    "ticks_1_gap_extra_2": {"slippage_ticks": 1, "gap_extra_ticks": 2},
    "ticks_1_partial_50pct": {"slippage_ticks": 1, "fill_fraction": 0.5},
    "harsh_4tick_gap2_partial50": {
        "slippage_ticks": 4,
        "gap_extra_ticks": 2,
        "fill_fraction": 0.5,
    },
}

# WF is the honest OOS; run it on the stresses that change the cost model most.
WF_NAMES = ("ticks_1_baseline", "ticks_2", "ticks_4", "harsh_4tick_gap2_partial50")


def _eng(extra: dict) -> dict:
    kw = dict(BASE_ENGINE)
    kw.update(extra)
    return kw


def _splits(df: pd.DataFrame, extra: dict) -> dict:
    cut = pd.Timestamp(HOLDOUT_OOS_START, tz=df.index.tz)
    eng = _eng(extra)
    strat = EnsembleStrategy(**STRAT_KW)
    out = {}
    for tag, d in (
        ("full", df),
        ("in_sample", df[df.index < cut]),
        ("holdout_oos", df[df.index >= cut]),
    ):
        res = run_backtest(d, strat, "MNQ", "5m", ACCOUNT, RISK_PCT, **eng)
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


def _wf(df: pd.DataFrame, extra: dict) -> dict:
    import src.backtest.walk_forward as wf

    orig = wf.run_backtest
    eng = _eng(extra)

    def _bt(d, strategy, symbol, timeframe, account_size, risk_pct, **_):
        return run_backtest(d, strategy, symbol, timeframe, account_size, risk_pct, **eng)

    wf.run_backtest = _bt  # type: ignore
    try:
        folds = walk_forward_search(
            df,
            EnsembleStrategy,
            {k: [v] for k, v in STRAT_KW.items()},
            "MNQ",
            "5m",
            ACCOUNT,
            RISK_PCT,
            WF_TRAIN_DAYS,
            WF_TEST_DAYS,
        )
        return aggregate_oos(folds)
    finally:
        wf.run_backtest = orig  # type: ignore


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    df = load_ohlcv("MNQ", "5m")
    rows = []
    print(
        "Sprint 4 fill audit — MNQ 5m ensemble (sprint-1 after). "
        "Paper only. Not an edge claim.\n",
        flush=True,
    )
    for name, extra in STRESSES.items():
        print(f"  {name} splits...", flush=True)
        splits = _splits(df, extra)
        oos = None
        if name in WF_NAMES:
            print(f"  {name} walk-forward...", flush=True)
            oos = _wf(df, extra)
            print(f"    WF {oos}", flush=True)
        print(
            f"    holdout pnl={splits['holdout_oos']['total_pnl']} "
            f"full={splits['full']['total_pnl']}",
            flush=True,
        )
        rows.append({"name": name, "extra": extra, "splits": splits, "walk_forward": oos})

    baseline_hold = next(r["splits"]["holdout_oos"]["total_pnl"] for r in rows if r["name"] == "ticks_1_baseline")
    baseline_wf = next(r["walk_forward"]["total_oos_pnl"] for r in rows if r["name"] == "ticks_1_baseline")
    payload = {
        "disclaimer": (
            "Paper/backtest only. The 1-tick MNQ ensemble was never a validated "
            "edge (t=1.76, MES failed). This audit asks whether even that "
            "fragile number survives harsher fills."
        ),
        "baseline_holdout_pnl": baseline_hold,
        "baseline_wf_pnl": baseline_wf,
        "rows": rows,
        "holdout_oos_start": HOLDOUT_OOS_START,
    }
    (OUT / "fill_audit.json").write_text(json.dumps(payload, indent=2, default=str))
    print("wrote", OUT / "fill_audit.json")


if __name__ == "__main__":
    main()
