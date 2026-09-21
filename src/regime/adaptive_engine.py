"""
Expectancy-driven adaptive backtest: at each candidate entry bar, ask every
strategy pool member currently firing a signal "what's your regime-
conditioned historical net expectancy, using only trades closed before this
moment?" and take the best one — provided it's positive and backed by at
least `min_sample` prior trades. Otherwise: no trade.

This replaces `RegimeAllocatorStrategy`'s argmax-on-a-heuristic-score
selection (which failed walk-forward testing) with a decision rule grounded
in measured historical outcomes, per the user's critique. Execution reuses
the same single-position/stop/target/trailing/breakeven mechanics as
`src/backtest/engine.py::run_backtest` — not reimplemented here.

On `transition_score` bars (regime actively shifting, see
`src/regime/engine.py`), risk_pct is halved for any trade taken, rather than
committing full size to an unsettled read.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

from config.instruments import get_spec
from config.settings import DEFAULT_MAX_CONTRACTS, DEFAULT_SLIPPAGE_TICKS
from src.backtest.engine import (
    ENGINE_DEFAULTS,
    BacktestResult,
    Trade,
    _slip,
    run_backtest,
)
from src.regime.engine import compute_regime_scores
from src.regime.expectancy_tracker import REGIME_COLUMNS, RegimeExpectancyTracker
from src.risk.position_sizing import contracts_for_risk
from src.strategies.base import Strategy
from src.strategies.indicators import atr

TRAIL_ATR_PERIOD = 14
TRAIL_ATR_MULT = 2.0
MIN_SAMPLE = 30
TRANSITION_THRESHOLD = 0.15
TRANSITION_RISK_MULT = 0.5


@dataclass
class ResearchLogRow:
    timestamp: pd.Timestamp
    trend_score: float
    range_score: float
    breakout_score: float
    transition_score: float
    transition: bool
    dominant_regime: str
    candidate_evs: Dict[str, Tuple[float, int]]  # strategy_name -> (expectancy, sample_size)
    selected_strategy: str  # or "no_trade"
    entry: float | None = None
    stop: float | None = None
    target: float | None = None
    position_size: int | None = None
    gross_pnl: float | None = None
    commission: float | None = None
    net_pnl: float | None = None
    equity_at_entry: float | None = None


def run_adaptive_backtest(
    df: pd.DataFrame,
    symbol: str,
    timeframe: str,
    strategy_pool: Dict[str, List[Strategy]],  # regime -> candidate strategies
    account_size: float,
    risk_pct: float,
    min_sample: int = MIN_SAMPLE,
    slippage_ticks: int = DEFAULT_SLIPPAGE_TICKS,
    max_contracts: int | None = DEFAULT_MAX_CONTRACTS,
) -> Tuple[BacktestResult, pd.DataFrame]:
    """Adaptive router with the same fill/risk defaults as `run_backtest`.

    Reference (solo) backtests and live fills both use next-open + exit
    slippage + gap-aware stops so this path is not secretly optimistic
    relative to the sprint-1 engine.
    """
    spec = get_spec(symbol)
    regime_scores = compute_regime_scores(df)

    all_strategies: Dict[str, Strategy] = {
        strat.name: strat for strategies in strategy_pool.values() for strat in strategies
    }
    regime_by_strategy_name = {
        strat.name: regime for regime, strategies in strategy_pool.items() for strat in strategies
    }

    # Independent reference backtests: each strategy's own trade history, as
    # if it traded every one of its own signals alone. This is purely the
    # expectancy-conditioning population — the adaptive loop below uses each
    # strategy's raw signal series directly for actual entry/stop/target,
    # since the adaptive engine's own position state is independent of
    # whichever bars the solo reference backtest happened to be mid-trade on.
    reference_results: Dict[str, BacktestResult] = {
        name: run_backtest(df, strat, symbol, timeframe, account_size, risk_pct, slippage_ticks)
        for name, strat in all_strategies.items()
    }
    all_signals = {name: strat.generate_signals(df) for name, strat in all_strategies.items()}
    all_entry_signals = {name: sig.entries for name, sig in all_signals.items()}
    all_stop_signals = {name: sig.stop_price for name, sig in all_signals.items()}
    all_target_signals = {name: sig.target_price for name, sig in all_signals.items()}

    tracker = RegimeExpectancyTracker(reference_results, regime_scores)

    trail_atr = atr(df["high"], df["low"], df["close"], TRAIL_ATR_PERIOD)
    apply_exit_slippage = ENGINE_DEFAULTS["apply_exit_slippage"]
    gap_aware_stops = ENGINE_DEFAULTS["gap_aware_stops"]

    trades: List[Trade] = []
    log_rows: List[ResearchLogRow] = []
    equity = account_size
    equity_curve = []

    position = None
    pending = None
    just_exited = False
    n = len(df)

    def _exit_fill(direction, raw_price, row, reason):
        mid = raw_price
        if reason in ("stop", "trail") and gap_aware_stops:
            if direction == 1 and row["open"] <= raw_price:
                mid = row["open"]
            elif direction == -1 and row["open"] >= raw_price:
                mid = row["open"]
        fill = mid + _slip(direction, slippage_ticks if apply_exit_slippage else 0, spec.tick_size, "exit")
        return fill, mid

    for i in range(n):
        ts = df.index[i]
        row = df.iloc[i]
        score_row = regime_scores.iloc[i]
        dominant_regime = max(REGIME_COLUMNS, key=lambda label: score_row[REGIME_COLUMNS[label]])
        transition = bool(score_row["transition_score"] >= TRANSITION_THRESHOLD)
        just_exited = False
        candidate_evs: Dict[str, Tuple[float, int]] = {}
        selected_strategy = "no_trade"
        row_extras: dict = {}

        if position is None and pending is not None:
            direction = pending["direction"]
            mid_entry = float(row["open"])
            entry_price = mid_entry + _slip(direction, slippage_ticks, spec.tick_size, "entry")
            stop = pending["stop"]
            gapped = gap_aware_stops and (
                (direction == 1 and row["open"] <= stop) or (direction == -1 and row["open"] >= stop)
            )
            if not gapped:
                contracts = contracts_for_risk(
                    equity, pending["risk_pct"], entry_price, stop, spec, max_contracts=max_contracts
                )
                if contracts > 0:
                    position = {
                        "direction": direction,
                        "entry_time": ts,
                        "entry_price": entry_price,
                        "mid_entry": mid_entry,
                        "stop": stop,
                        "target": pending["target"],
                        "contracts": contracts,
                        "trailing": pending["target"] is None,
                        "trail_extreme": mid_entry,
                        "initial_risk": abs(entry_price - stop),
                        "breakeven_triggered": False,
                    }
                    selected_strategy = pending["name"]
                    candidate_evs = pending["candidate_evs"]
                    transition = pending["transition"]
                    row_extras = {
                        "entry": entry_price,
                        "stop": stop,
                        "target": pending["target"],
                        "position_size": contracts,
                        "equity_at_entry": equity,
                    }
            pending = None

        if position is not None:
            direction = position["direction"]
            stop_at_open = position["stop"]
            target_at_open = position["target"]
            trailing_at_open = position["trailing"]

            exit_price, exit_reason, mid_exit = None, None, None
            if direction == 1:
                if row["low"] <= stop_at_open:
                    reason = "trail" if trailing_at_open else "stop"
                    exit_price, mid_exit = _exit_fill(direction, stop_at_open, row, reason)
                    exit_reason = reason
                elif target_at_open is not None and row["high"] >= target_at_open:
                    mid_exit = target_at_open
                    exit_price = mid_exit + _slip(
                        direction, slippage_ticks if apply_exit_slippage else 0, spec.tick_size, "exit"
                    )
                    exit_reason = "target"
            else:
                if row["high"] >= stop_at_open:
                    reason = "trail" if trailing_at_open else "stop"
                    exit_price, mid_exit = _exit_fill(direction, stop_at_open, row, reason)
                    exit_reason = reason
                elif target_at_open is not None and row["low"] <= target_at_open:
                    mid_exit = target_at_open
                    exit_price = mid_exit + _slip(
                        direction, slippage_ticks if apply_exit_slippage else 0, spec.tick_size, "exit"
                    )
                    exit_reason = "target"

            if i == n - 1 and exit_price is None:
                mid_exit = float(row["close"])
                exit_price = mid_exit + _slip(
                    direction, slippage_ticks if apply_exit_slippage else 0, spec.tick_size, "exit"
                )
                exit_reason = "eod"

            if exit_price is not None:
                ticks = (exit_price - position["entry_price"]) / spec.tick_size * direction
                gross_pnl = ticks * spec.tick_value_usd * position["contracts"]
                commission = spec.commission_rt * position["contracts"]
                pnl = gross_pnl - commission
                entry_slip = abs(position["entry_price"] - position.get("mid_entry", position["entry_price"])) / spec.tick_size
                exit_slip = abs(exit_price - (mid_exit if mid_exit is not None else exit_price)) / spec.tick_size
                slippage_cost = (entry_slip + exit_slip) * spec.tick_value_usd * position["contracts"]
                equity += pnl
                trades.append(
                    Trade(
                        symbol=symbol, direction=direction, entry_time=position["entry_time"],
                        entry_price=position["entry_price"], exit_time=ts, exit_price=exit_price,
                        contracts=position["contracts"], gross_pnl=gross_pnl, commission=commission,
                        pnl=pnl, exit_reason=exit_reason, slippage_cost=float(slippage_cost),
                    )
                )
                position = None
                just_exited = True
            else:
                if direction == 1:
                    position["trail_extreme"] = max(position["trail_extreme"], row["high"])
                    if (row["high"] - position["entry_price"]) >= position["initial_risk"]:
                        position["stop"] = max(position["stop"], position["entry_price"])
                        position["breakeven_triggered"] = True
                    if position["trailing"] and not pd.isna(trail_atr.iloc[i]):
                        candidate = position["trail_extreme"] - TRAIL_ATR_MULT * trail_atr.iloc[i]
                        position["stop"] = max(position["stop"], candidate)
                else:
                    position["trail_extreme"] = min(position["trail_extreme"], row["low"])
                    if (position["entry_price"] - row["low"]) >= position["initial_risk"]:
                        position["stop"] = min(position["stop"], position["entry_price"])
                        position["breakeven_triggered"] = True
                    if position["trailing"] and not pd.isna(trail_atr.iloc[i]):
                        candidate = position["trail_extreme"] + TRAIL_ATR_MULT * trail_atr.iloc[i]
                        position["stop"] = min(position["stop"], candidate)

        if position is None and pending is None and (not just_exited) and i < n - 1:
            best_name, best_ev = None, 0.0
            for name, strat in all_strategies.items():
                if all_entry_signals[name].iloc[i] == 0:
                    continue
                regime = regime_by_strategy_name[name]
                ev, sample_n = tracker.expectancy_as_of(regime, name, ts)
                candidate_evs[name] = (ev, sample_n)
                if sample_n < min_sample:
                    continue
                if ev > best_ev:
                    best_name, best_ev = name, ev

            if best_name is not None:
                direction = int(all_entry_signals[best_name].iloc[i])
                raw_stop = all_stop_signals[best_name].iloc[i]
                if not np.isnan(raw_stop):
                    strat_target = all_target_signals[best_name].iloc[i]
                    target = None if np.isnan(strat_target) else float(strat_target)
                    pending = {
                        "name": best_name,
                        "direction": direction,
                        "stop": float(raw_stop),
                        "target": target,
                        "risk_pct": risk_pct * TRANSITION_RISK_MULT if transition else risk_pct,
                        "transition": transition,
                        "candidate_evs": candidate_evs,
                    }

        log_rows.append(
            ResearchLogRow(
                timestamp=ts,
                trend_score=score_row["trend_score"], range_score=score_row["range_score"],
                breakout_score=score_row["breakout_score"], transition_score=score_row["transition_score"],
                transition=transition, dominant_regime=dominant_regime,
                candidate_evs=candidate_evs, selected_strategy=selected_strategy,
                **row_extras,
            )
        )

        equity_curve.append((ts, equity))

    equity_series = pd.Series([v for _, v in equity_curve], index=[t for t, _ in equity_curve], name="equity")
    result = BacktestResult(symbol=symbol, strategy="adaptive", timeframe=timeframe, trades=trades, equity_curve=equity_series)

    log_df = pd.DataFrame([
        {
            "timestamp": r.timestamp, "trend_score": r.trend_score, "range_score": r.range_score,
            "breakout_score": r.breakout_score, "transition_score": r.transition_score,
            "transition": r.transition, "dominant_regime": r.dominant_regime,
            "selected_strategy": r.selected_strategy,
            "entry": r.entry, "stop": r.stop, "target": r.target, "position_size": r.position_size,
            "equity_at_entry": r.equity_at_entry,
            **{f"{name}_ev": ev for name, (ev, _) in r.candidate_evs.items()},
            **{f"{name}_ev_n": n_ for name, (_, n_) in r.candidate_evs.items()},
        }
        for r in log_rows
    ])

    # Attach gross/commission/net for the bars where a trade actually closed
    # (joined by exit_time, since that's when those numbers exist). Always
    # present as columns, even with zero closed trades, so the schema is
    # consistent regardless of how many trades happened to close.
    trade_df = pd.DataFrame(
        {"timestamp": [t.exit_time for t in trades], "gross_pnl": [t.gross_pnl for t in trades],
         "commission": [t.commission for t in trades], "net_pnl": [t.pnl for t in trades]}
    )
    if trade_df.empty:
        for col in ("gross_pnl", "commission", "net_pnl"):
            log_df[col] = np.nan
    else:
        log_df = log_df.merge(trade_df, on="timestamp", how="left")

    return result, log_df
