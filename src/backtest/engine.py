"""
Generic bar-by-bar backtest engine.

Single open position at a time. A strategy's `generate_signals` supplies an
entry direction and initial stop per bar; when `target_price` is NaN the
engine runs an ATR-trailing stop instead of a fixed take-profit (used by the
trend-following and breakout strategies, which aim to let winners run).

Default fill model (`next_open`):
  - Signal is read at bar close, fill is the *next* bar's open +/- slippage.
  - Stops that gap through fill at the gapped open (worse), not the stop.
  - Exit slippage is applied on stop/target/trail (same tick count as entry).
  - Trailing stop uses the stop as of the *bar open* for the exit check, then
    updates for the next bar (avoids OHLC high-then-tighten-then-low-hits-new-stop).
  - A trade cannot re-enter on the same bar it exited.

Legacy fill model (`signal_close`) is preserved so sprint-1 "before" numbers
can be reproduced: fill at the signal bar close, no exit slippage, same-bar
trail tightening, optional same-bar re-entry.

A strategy may optionally set `self.breakeven_r_mult = <float>` to move the
stop to entry price once favorable excursion reaches that many multiples of
initial risk. Under `trail_update="next_bar"` the move applies from the
following bar, not the triggering bar.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
import math

import numpy as np
import pandas as pd

from config.instruments import get_spec
from config.settings import DEFAULT_MAX_CONTRACTS, DEFAULT_SLIPPAGE_TICKS
from src.backtest.session import last_rth_bar_mask, rth_mask, session_date
from src.risk.position_sizing import contracts_for_risk
from src.strategies.base import Strategy, StrategySignals
from src.strategies.indicators import atr

TRAIL_ATR_PERIOD = 14
TRAIL_ATR_MULT = 2.0

# Defaults after sprint-1 fill/risk fixes. The improve-loop "before" phase
# overrides these to the pre-sprint engine so the comparison is apples-to-apples.
ENGINE_DEFAULTS = {
    "fill_model": "next_open",
    "apply_exit_slippage": True,
    "gap_aware_stops": True,
    "trail_update": "next_bar",
    "cooldown_bars": 0,
    "allow_same_bar_reentry": False,
    "daily_loss_halt_pct": None,
    "flatten_at_rth_close": False,
    "max_contracts": DEFAULT_MAX_CONTRACTS,
    "rth_entries_only": False,
    "min_atr_gate": False,
    "max_cost_frac_of_risk": None,
    "skip_rth_open_minutes": 0,
    "gap_extra_ticks": 0,
    "fill_fraction": 1.0,
}


@dataclass
class Trade:
    symbol: str
    direction: int  # 1 long, -1 short
    entry_time: pd.Timestamp
    entry_price: float
    exit_time: pd.Timestamp
    exit_price: float
    contracts: int
    gross_pnl: float
    commission: float
    pnl: float  # net = gross_pnl - commission
    exit_reason: str  # "stop" | "target" | "trail" | "eod" | "flatten"
    slippage_cost: float = 0.0


@dataclass
class BacktestResult:
    symbol: str
    strategy: str
    timeframe: str
    trades: List[Trade] = field(default_factory=list)
    equity_curve: pd.Series = field(default_factory=pd.Series)


def _slip(direction: int, ticks: int, tick_size: float, side: str) -> float:
    """Price adjustment: longs pay up on entry / down on exit; shorts the reverse."""
    signed = ticks * tick_size
    if side == "entry":
        return direction * signed
    return -direction * signed


def _cost_ok(entry_price: float, stop: float, spec, slippage_ticks: int, max_cost_frac: Optional[float]) -> bool:
    if max_cost_frac is None:
        return True
    ticks_at_risk = abs(entry_price - stop) / spec.tick_size
    dollar_risk = ticks_at_risk * spec.tick_value_usd
    if dollar_risk <= 0:
        return False
    rt_cost = spec.commission_rt + 2 * slippage_ticks * spec.tick_value_usd
    return (rt_cost / dollar_risk) <= max_cost_frac


def run_backtest(
    df: pd.DataFrame,
    strategy: Strategy,
    symbol: str,
    timeframe: str,
    account_size: float,
    risk_pct: float,
    slippage_ticks: int = DEFAULT_SLIPPAGE_TICKS,
    fill_model: str = ENGINE_DEFAULTS["fill_model"],
    apply_exit_slippage: bool = ENGINE_DEFAULTS["apply_exit_slippage"],
    gap_aware_stops: bool = ENGINE_DEFAULTS["gap_aware_stops"],
    trail_update: str = ENGINE_DEFAULTS["trail_update"],
    cooldown_bars: int = ENGINE_DEFAULTS["cooldown_bars"],
    allow_same_bar_reentry: bool = ENGINE_DEFAULTS["allow_same_bar_reentry"],
    daily_loss_halt_pct: Optional[float] = ENGINE_DEFAULTS["daily_loss_halt_pct"],
    flatten_at_rth_close: bool = ENGINE_DEFAULTS["flatten_at_rth_close"],
    max_contracts: Optional[int] = ENGINE_DEFAULTS["max_contracts"],
    rth_entries_only: bool = ENGINE_DEFAULTS["rth_entries_only"],
    min_atr_gate: bool = ENGINE_DEFAULTS["min_atr_gate"],
    max_cost_frac_of_risk: Optional[float] = ENGINE_DEFAULTS["max_cost_frac_of_risk"],
    skip_rth_open_minutes: int = ENGINE_DEFAULTS["skip_rth_open_minutes"],
    gap_extra_ticks: int = ENGINE_DEFAULTS["gap_extra_ticks"],
    fill_fraction: float = ENGINE_DEFAULTS["fill_fraction"],
) -> BacktestResult:
    spec = get_spec(symbol)
    signals: StrategySignals = strategy.generate_signals(df)
    trail_atr = atr(df["high"], df["low"], df["close"], TRAIL_ATR_PERIOD)
    slippage_price = slippage_ticks * spec.tick_size
    exit_slip_price = slippage_price if apply_exit_slippage else 0.0
    breakeven_r_mult = getattr(strategy, "breakeven_r_mult", None)

    need_rth = bool(flatten_at_rth_close or rth_entries_only or skip_rth_open_minutes)
    rth = rth_mask(df.index) if need_rth else None
    last_rth = last_rth_bar_mask(df.index) if flatten_at_rth_close else None
    sess_dates = session_date(df.index) if daily_loss_halt_pct else None
    rth_open_mins = None
    if skip_rth_open_minutes:
        from src.backtest.session import minutes_since_rth_open

        rth_open_mins = minutes_since_rth_open(df.index)

    trades: List[Trade] = []
    equity = account_size
    equity_curve = []

    position: Optional[dict] = None
    pending: Optional[dict] = None
    n = len(df)
    cooldown_until = -1
    day_start_equity = equity
    day_realized = 0.0
    current_day = None
    just_exited = False

    def _close_trade(i, ts, row, exit_price, exit_reason, mid_exit):
        nonlocal equity, position, just_exited, day_realized
        direction = position["direction"]
        ticks = (exit_price - position["entry_price"]) / spec.tick_size * direction
        gross_pnl = ticks * spec.tick_value_usd * position["contracts"]
        commission = spec.commission_rt * position["contracts"]
        pnl = gross_pnl - commission
        entry_slip_ticks = abs(position["entry_price"] - position["mid_entry"]) / spec.tick_size
        exit_slip_ticks = abs(exit_price - mid_exit) / spec.tick_size
        slippage_cost = (entry_slip_ticks + exit_slip_ticks) * spec.tick_value_usd * position["contracts"]
        equity += pnl
        day_realized += pnl
        trades.append(
            Trade(
                symbol=symbol,
                direction=direction,
                entry_time=position["entry_time"],
                entry_price=position["entry_price"],
                exit_time=ts,
                exit_price=exit_price,
                contracts=position["contracts"],
                gross_pnl=gross_pnl,
                commission=commission,
                pnl=pnl,
                exit_reason=exit_reason,
                slippage_cost=float(slippage_cost),
            )
        )
        position = None
        just_exited = True

    def _apply_fill_fraction(n: int) -> int:
        if n <= 0:
            return 0
        if fill_fraction >= 1.0:
            return n
        return max(0, math.floor(n * fill_fraction))

    def _exit_fill(direction, raw_price, row, reason):
        """Apply gap-aware / slippage rules to a theoretical stop or target price."""
        mid = raw_price
        extra = 0
        if reason in ("stop", "trail") and gap_aware_stops:
            gapped = (direction == 1 and row["open"] <= raw_price) or (
                direction == -1 and row["open"] >= raw_price
            )
            if gapped:
                mid = row["open"]
                extra = gap_extra_ticks
        fill = mid + _slip(
            direction,
            (slippage_ticks if apply_exit_slippage else 0) + extra,
            spec.tick_size,
            "exit",
        )
        return fill, mid

    for i in range(n):
        ts = df.index[i]
        row = df.iloc[i]
        just_exited = False

        if sess_dates is not None:
            d = sess_dates.iloc[i]
            if d != current_day:
                current_day = d
                day_start_equity = equity
                day_realized = 0.0

        # Fill a pending next-open entry at this bar's open.
        if position is None and pending is not None:
            if rth is not None and (flatten_at_rth_close or rth_entries_only) and not bool(rth.iloc[i]):
                pending = None
            else:
                direction = pending["direction"]
                mid_entry = float(row["open"])
                entry_price = mid_entry + _slip(direction, slippage_ticks, spec.tick_size, "entry")
                stop = pending["stop"]
                gapped_through = (
                    gap_aware_stops
                    and (
                        (direction == 1 and row["open"] <= stop)
                        or (direction == -1 and row["open"] >= stop)
                    )
                )
                if not gapped_through:
                    if not _cost_ok(entry_price, stop, spec, slippage_ticks, max_cost_frac_of_risk):
                        contracts = 0
                    else:
                        contracts = contracts_for_risk(
                            equity, risk_pct, entry_price, stop, spec, max_contracts=max_contracts
                        )
                        contracts = _apply_fill_fraction(contracts)
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
            pending = None

        if position is not None:
            direction = position["direction"]
            stop_at_open = position["stop"]
            target_at_open = position["target"]
            trailing_at_open = position["trailing"]

            # Same-bar trail: tighten using this bar's extreme BEFORE the exit
            # check (legacy, optimistic on OHLC ambiguity). next_bar: check first.
            if trail_update == "same_bar":
                if direction == 1:
                    position["trail_extreme"] = max(position["trail_extreme"], row["high"])
                    if breakeven_r_mult is not None and not position["breakeven_triggered"]:
                        if (row["high"] - position["entry_price"]) >= breakeven_r_mult * position["initial_risk"]:
                            position["stop"] = max(position["stop"], position["entry_price"])
                            position["breakeven_triggered"] = True
                    if position["trailing"]:
                        atr_i = trail_atr.iloc[i]
                        if not pd.isna(atr_i):
                            candidate = position["trail_extreme"] - TRAIL_ATR_MULT * atr_i
                            position["stop"] = max(position["stop"], candidate)
                else:
                    position["trail_extreme"] = min(position["trail_extreme"], row["low"])
                    if breakeven_r_mult is not None and not position["breakeven_triggered"]:
                        if (position["entry_price"] - row["low"]) >= breakeven_r_mult * position["initial_risk"]:
                            position["stop"] = min(position["stop"], position["entry_price"])
                            position["breakeven_triggered"] = True
                    if position["trailing"]:
                        atr_i = trail_atr.iloc[i]
                        if not pd.isna(atr_i):
                            candidate = position["trail_extreme"] + TRAIL_ATR_MULT * atr_i
                            position["stop"] = min(position["stop"], candidate)
                stop_for_exit = position["stop"]
                target_for_exit = position["target"]
                trailing_for_exit = position["trailing"]
            else:
                stop_for_exit = stop_at_open
                target_for_exit = target_at_open
                trailing_for_exit = trailing_at_open

            exit_price = None
            exit_reason = None
            mid_exit = None
            flatten_now = bool(flatten_at_rth_close and last_rth is not None and last_rth.iloc[i])

            if direction == 1:
                if row["low"] <= stop_for_exit:
                    reason = "trail" if trailing_for_exit else "stop"
                    exit_price, mid_exit = _exit_fill(direction, stop_for_exit, row, reason)
                    exit_reason = reason
                elif target_for_exit is not None and row["high"] >= target_for_exit:
                    # Conservative: never fill a gap-through target better than the target.
                    mid_exit = target_for_exit
                    exit_price = mid_exit + _slip(
                        direction, slippage_ticks if apply_exit_slippage else 0, spec.tick_size, "exit"
                    )
                    exit_reason = "target"
            else:
                if row["high"] >= stop_for_exit:
                    reason = "trail" if trailing_for_exit else "stop"
                    exit_price, mid_exit = _exit_fill(direction, stop_for_exit, row, reason)
                    exit_reason = reason
                elif target_for_exit is not None and row["low"] <= target_for_exit:
                    mid_exit = target_for_exit
                    exit_price = mid_exit + _slip(
                        direction, slippage_ticks if apply_exit_slippage else 0, spec.tick_size, "exit"
                    )
                    exit_reason = "target"

            if flatten_now and exit_price is None:
                mid_exit = float(row["close"])
                exit_price = mid_exit + _slip(
                    direction, slippage_ticks if apply_exit_slippage else 0, spec.tick_size, "exit"
                )
                exit_reason = "flatten"

            if i == n - 1 and exit_price is None:
                mid_exit = float(row["close"])
                exit_price = mid_exit + _slip(
                    direction, slippage_ticks if apply_exit_slippage else 0, spec.tick_size, "exit"
                )
                exit_reason = "eod"

            if exit_price is not None:
                _close_trade(i, ts, row, exit_price, exit_reason, mid_exit)
                cooldown_until = i + max(cooldown_bars, 0) + (0 if allow_same_bar_reentry else 0)
                if not allow_same_bar_reentry:
                    cooldown_until = max(cooldown_until, i + 1)
                if cooldown_bars:
                    cooldown_until = max(cooldown_until, i + cooldown_bars)

            elif trail_update == "next_bar":
                if direction == 1:
                    position["trail_extreme"] = max(position["trail_extreme"], row["high"])
                    if breakeven_r_mult is not None and not position["breakeven_triggered"]:
                        if (row["high"] - position["entry_price"]) >= breakeven_r_mult * position["initial_risk"]:
                            position["stop"] = max(position["stop"], position["entry_price"])
                            position["breakeven_triggered"] = True
                    if position["trailing"]:
                        atr_i = trail_atr.iloc[i]
                        if not (pd.isna(atr_i)):
                            candidate = position["trail_extreme"] - TRAIL_ATR_MULT * atr_i
                            position["stop"] = max(position["stop"], candidate)
                else:
                    position["trail_extreme"] = min(position["trail_extreme"], row["low"])
                    if breakeven_r_mult is not None and not position["breakeven_triggered"]:
                        if (position["entry_price"] - row["low"]) >= breakeven_r_mult * position["initial_risk"]:
                            position["stop"] = min(position["stop"], position["entry_price"])
                            position["breakeven_triggered"] = True
                    if position["trailing"]:
                        atr_i = trail_atr.iloc[i]
                        if not (pd.isna(atr_i)):
                            candidate = position["trail_extreme"] + TRAIL_ATR_MULT * atr_i
                            position["stop"] = min(position["stop"], candidate)

        # New signals: legacy fills at this close; next_open queues for the following open.
        can_signal = position is None and pending is None
        if can_signal and not allow_same_bar_reentry and just_exited:
            can_signal = False
        if can_signal and i < cooldown_until:
            can_signal = False
        if can_signal and daily_loss_halt_pct is not None:
            halt_level = -abs(daily_loss_halt_pct) / 100.0 * day_start_equity
            if day_realized <= halt_level:
                can_signal = False
        if can_signal and flatten_at_rth_close and last_rth is not None and bool(last_rth.iloc[i]):
            can_signal = False  # would fill after the cash close
        if can_signal and rth_entries_only and rth is not None and not bool(rth.iloc[i]):
            can_signal = False
        if can_signal and skip_rth_open_minutes and rth_open_mins is not None:
            mins = int(rth_open_mins.iloc[i])
            if mins < skip_rth_open_minutes:
                can_signal = False
        if can_signal and min_atr_gate:
            atr_i = trail_atr.iloc[i]
            if pd.isna(atr_i) or float(atr_i) < spec.atr_minimum:
                can_signal = False

        if can_signal:
            entry_signal = signals.entries.iloc[i]
            if entry_signal != 0:
                direction = int(entry_signal)
                raw_stop = signals.stop_price.iloc[i]
                raw_target = signals.target_price.iloc[i]
                if not np.isnan(raw_stop):
                    target = None if np.isnan(raw_target) else float(raw_target)
                    if fill_model == "signal_close":
                        if i < n - 1:
                            mid_entry = float(row["close"])
                            entry_price = mid_entry + _slip(direction, slippage_ticks, spec.tick_size, "entry")
                            stop = float(raw_stop)
                            if not _cost_ok(entry_price, stop, spec, slippage_ticks, max_cost_frac_of_risk):
                                contracts = 0
                            else:
                                contracts = contracts_for_risk(
                                    equity, risk_pct, entry_price, stop, spec, max_contracts=max_contracts
                                )
                                contracts = _apply_fill_fraction(contracts)
                            if contracts > 0:
                                position = {
                                    "direction": direction,
                                    "entry_time": ts,
                                    "entry_price": entry_price,
                                    "mid_entry": mid_entry,
                                    "stop": stop,
                                    "target": target,
                                    "contracts": contracts,
                                    "trailing": target is None,
                                    "trail_extreme": row["high"] if direction == 1 else row["low"],
                                    "initial_risk": abs(entry_price - stop),
                                    "breakeven_triggered": False,
                                }
                    else:
                        if i < n - 1:
                            pending = {
                                "direction": direction,
                                "stop": float(raw_stop),
                                "target": target,
                            }

        equity_curve.append((ts, equity))

    equity_series = pd.Series(
        [v for _, v in equity_curve], index=[t for t, _ in equity_curve], name="equity"
    )
    return BacktestResult(symbol=symbol, strategy=strategy.name, timeframe=timeframe, trades=trades, equity_curve=equity_series)
