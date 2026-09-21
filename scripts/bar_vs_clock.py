"""Clock / weekday baseline vs OHLC path on MNQ discovery.

If a pure clock or weekday long/short clears t≥2, the edge is not in the
candlestick path. If nothing does, 5m OHLCV on this 2024–now tape has not
shown a kill-gate MNQ edge from either bars or calendar.

Paper / backtest only. Discovery tape only (before holdout).
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
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
from src.strategies.base import StrategySignals
from src.strategies.session import (
    FLATTEN_1545,
    RTH_CLOSE_MINUTES,
    RTH_OPEN_MINUTES,
    prior_day_atr,
    session_clock,
    short_session_dates,
)


class _ClockBias:
    flatten_rth = True
    rth_flatten_minutes = RTH_CLOSE_MINUTES
    rth_entry_cutoff_minutes = FLATTEN_1545
    session_exit_minutes = FLATTEN_1545
    max_hold_bars = 78

    def __init__(self, name: str, direction: int, weekdays: tuple | None = None):
        self.name = name
        self.direction = int(direction)
        self.weekdays = weekdays

    def generate_signals(self, df: pd.DataFrame) -> StrategySignals:
        minutes, dates = session_clock(df.index)
        mins = minutes.to_numpy()
        date_vals = dates.to_numpy()
        close = df["close"].to_numpy()
        atr_ = prior_day_atr(df, dates).to_numpy()
        holidays = short_session_dates(df)
        entries = np.zeros(len(df), dtype=int)
        stops = np.full(len(df), np.nan)
        targets = np.full(len(df), np.nan)
        for d in pd.unique(date_vals):
            if d in holidays:
                continue
            if self.weekdays is not None and pd.Timestamp(d).weekday() not in self.weekdays:
                continue
            idx = np.where((date_vals == d) & (mins == RTH_OPEN_MINUTES))[0]
            if len(idx) == 0:
                idx = np.where(
                    (date_vals == d) & (mins >= RTH_OPEN_MINUTES) & (mins < RTH_OPEN_MINUTES + 5)
                )[0]
            if len(idx) == 0:
                continue
            i = int(idx[0])
            day_atr = float(atr_[i]) if not np.isnan(atr_[i]) else 1.0
            if day_atr <= 0:
                day_atr = 1.0
            entries[i] = self.direction
            stops[i] = close[i] - self.direction * 0.35 * day_atr
            targets[i] = close[i] + self.direction * 0.35 * day_atr
        return StrategySignals(
            entries=pd.Series(entries, index=df.index),
            stop_price=pd.Series(stops, index=df.index),
            target_price=pd.Series(targets, index=df.index),
        )


def diagnose(df: pd.DataFrame, symbol: str, timeframe: str = "5m") -> Dict[str, Any]:
    cut = pd.Timestamp(HOLDOUT_OOS_START, tz=df.index.tz)
    discovery = df[df.index < cut]
    rows: List[Dict[str, Any]] = []
    specs = [
        ("clock_long_rth", 1, None),
        ("clock_short_rth", -1, None),
        ("tue_thu_long", 1, (1, 2, 3)),
        ("mon_fri_long", 1, (0, 4)),
    ]
    for name, direction, days in specs:
        strat = _ClockBias(name, direction, days)
        res = run_backtest(
            discovery, strat, symbol, timeframe, ACCOUNT_SIZE, RISK_PCT, **SPRINT1_AFTER_ENGINE
        )
        pnls = [t.pnl for t in res.trades]
        t = _t_stat(pnls)
        n = len(pnls)
        rows.append(
            {
                "name": name,
                "n": n,
                "t_stat": round(t, 3) if t is not None else None,
                "pnl": round(float(sum(pnls)), 2) if pnls else 0.0,
                "clears_gate": bool(n >= KILL_MIN_TRADES and t is not None and t >= KILL_T_STAT),
            }
        )
    any_clock = any(r["clears_gate"] for r in rows)
    return {
        "generated": datetime.now(timezone.utc).isoformat(),
        "symbol": symbol,
        "tape_rows": int(len(discovery)),
        "verdict": "CLOCK_EDGE" if any_clock else "NOT_IN_CLOCK_OR_BARS_YET",
        "note": (
            "CLOCK_EDGE means a weekday/time-of-day long/short cleared t>=2 "
            "without a candlestick pattern. Otherwise "
            f"{symbol} {timeframe} OHLCV on this 2024–now tape has not shown "
            "a kill-gate edge from calendar either."
        ),
        "baselines": rows,
    }


def write_report(payload: Dict[str, Any], dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / "bar_vs_clock.json").write_text(json.dumps(payload, indent=2, default=str))
    lines = [
        "# Bar vs clock (MNQ discovery)",
        "",
        "Paper / backtest only. Sprint-1 fills. No live trading.",
        "",
        f"Verdict: **{payload['verdict']}**",
        "",
        "| Baseline | n | t | PnL | Gate |",
        "|---|---:|---:|---:|---|",
    ]
    for r in payload["baselines"]:
        gate = "PASS" if r["clears_gate"] else "no"
        lines.append(f"| {r['name']} | {r['n']} | {r['t_stat']} | {r['pnl']} | {gate} |")
    lines.extend(["", payload["note"], ""])
    (dest / "BAR_VS_CLOCK.md").write_text("\n".join(lines))
