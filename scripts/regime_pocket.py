"""ADX / year / ATR-tercile pocket diagnostic for original EMA trend + Donchian.

If no pocket on the discovery tape clears t ≥ 2.0 with n ≥ 30 under sprint-1
fills, leave `trend` and `breakout` dead — do not retune them into the hunt.

Paper / backtest only. No live trading.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from src.backtest.engine import run_backtest
from src.backtest.walk_forward import _t_stat
from src.research.presets import (
    ACCOUNT_SIZE,
    HOLDOUT_OOS_START,
    KILL_MIN_TRADES,
    KILL_T_STAT,
    RISK_PCT,
    SPRINT1_AFTER_ENGINE,
)
from src.strategies.breakout import BreakoutStrategy
from src.strategies.indicators import adx, atr
from src.strategies.trend_following import TrendFollowingStrategy


def _tercile_labels(series: pd.Series) -> pd.Series:
    valid = series.dropna()
    if len(valid) < 9:
        return pd.Series("na", index=series.index)
    try:
        return pd.qcut(series, 3, labels=["lo", "mid", "hi"], duplicates="drop").astype(str)
    except (ValueError, TypeError):
        return pd.Series("na", index=series.index)


def _pocket_table(pnls_by_key: Dict[str, List[float]]) -> List[Dict[str, Any]]:
    rows = []
    for key, pnls in sorted(pnls_by_key.items()):
        t = _t_stat(pnls)
        n = len(pnls)
        rows.append(
            {
                "pocket": key,
                "n": n,
                "t_stat": round(t, 3) if t is not None else None,
                "pnl": round(float(sum(pnls)), 2),
                "clears_gate": bool(n >= KILL_MIN_TRADES and t is not None and t >= KILL_T_STAT),
            }
        )
    return rows


def diagnose_symbol(df: pd.DataFrame, symbol: str, timeframe: str = "5m") -> Dict[str, Any]:
    cut = pd.Timestamp(HOLDOUT_OOS_START, tz=df.index.tz)
    discovery = df[df.index < cut]
    adx_ = adx(discovery["high"], discovery["low"], discovery["close"])
    atr_ = atr(discovery["high"], discovery["low"], discovery["close"])
    adx_bin = _tercile_labels(adx_)
    atr_bin = _tercile_labels(atr_)

    out: Dict[str, Any] = {"symbol": symbol, "tape_rows": int(len(discovery)), "families": {}}
    for name, cls in (("trend", TrendFollowingStrategy), ("breakout", BreakoutStrategy)):
        result = run_backtest(
            discovery, cls(), symbol, timeframe, ACCOUNT_SIZE, RISK_PCT, **SPRINT1_AFTER_ENGINE
        )
        by_year: Dict[str, List[float]] = defaultdict(list)
        by_adx: Dict[str, List[float]] = defaultdict(list)
        by_atr: Dict[str, List[float]] = defaultdict(list)
        overnight = 0
        for t in result.trades:
            local = t.entry_time.tz_convert("America/New_York") if t.entry_time.tzinfo else t.entry_time
            by_year[str(local.year)].append(t.pnl)
            loc = discovery.index.get_indexer([t.entry_time], method="ffill")[0]
            if loc >= 0:
                by_adx[f"adx_{adx_bin.iloc[loc]}"].append(t.pnl)
                by_atr[f"atr_{atr_bin.iloc[loc]}"].append(t.pnl)
            local_exit = t.exit_time.tz_convert("America/New_York")
            if local_exit.hour > 16 or (local_exit.hour == 16 and local_exit.minute > 5):
                overnight += 1
        all_pnls = [tr.pnl for tr in result.trades]
        pockets = _pocket_table(by_year) + _pocket_table(by_adx) + _pocket_table(by_atr)
        live_pockets = [p for p in pockets if p["clears_gate"]]
        out["families"][name] = {
            "n": len(all_pnls),
            "t_stat": round(_t_stat(all_pnls), 3) if _t_stat(all_pnls) is not None else None,
            "pnl": round(float(sum(all_pnls)), 2) if all_pnls else 0.0,
            "held_past_rth_close": overnight,
            "pockets": pockets,
            "gate_pockets": live_pockets,
            "verdict": "POCKET" if live_pockets else "LEAVE_DEAD",
        }
    return out


def write_report(payloads: List[Dict[str, Any]], dest: Path) -> Dict[str, Any]:
    dest.mkdir(parents=True, exist_ok=True)
    any_pocket = any(
        fam["verdict"] == "POCKET" for p in payloads for fam in p["families"].values()
    )
    summary = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "verdict": "POCKET" if any_pocket else "LEAVE_DEAD",
        "note": (
            "Improve original EMA/Donchian only if a discovery pocket clears "
            "t>=2 n>=30. Otherwise leave dead."
        ),
        "symbols": payloads,
    }
    (dest / "regime_pockets.json").write_text(json.dumps(summary, indent=2, default=str))
    lines = [
        "# EMA / Donchian regime pockets",
        "",
        "Paper / backtest only. Sprint-1 fills. Discovery tape only (before holdout).",
        "",
        f"Verdict: **{summary['verdict']}**",
        "",
        "| Symbol | Family | n | t | Pockets t≥2 n≥30 | Label |",
        "|---|---|---:|---:|---|---|",
    ]
    for p in payloads:
        for name, fam in p["families"].items():
            hits = ", ".join(x["pocket"] for x in fam["gate_pockets"]) or "—"
            lines.append(
                f"| {p['symbol']} | {name} | {fam['n']} | {fam['t_stat']} | {hits} | {fam['verdict']} |"
            )
    lines.extend(["", "Leave dead unless a pocket row is POCKET.", ""])
    (dest / "REGIME_POCKETS.md").write_text("\n".join(lines))
    return summary
