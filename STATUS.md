# STATUS — RTH session strategies (paper / backtest only)

This sprint adds three **new** intra-session modules. They are not EMA / Donchian / ADX retunes of the existing suite. Live trading is out of scope. Nothing here is a profit claim.

## Constraints enforced

- Primary session is RTH (09:30–16:00 America/New_York). No overnight-only designs.
- Anti-cling: hard `max_hold_bars`, flatten at cash close (`rth_flatten`), no averaging down (engine is still one position), no holding losers overnight.
- Fills stay on the sprint-1 engine: signal-bar close + 1 tick; stop/target on later bars. Clock exits fill at close ± 1 tick.
- Kill rule: walk-forward OOS t-stat < 2 **or** MES fails to replicate.

## Modules

| Name | Mechanism | Exit |
|---|---|---|
| `orb_break_fade` | Combined opening-range break + failure-fade state machine | 1.5R target, stop at broken level / failed extreme, time stop, 16:00 flatten |
| `vol_squeeze_expansion` | BB-inside-Keltner + width-percentile squeeze, volume break | 1.5R, opposite BB, time stop, 16:00 flatten |
| `impulse_clock` | Large-range directional bar continuation | 1.5R, impulse extreme, max 8 bars default, 16:00 flatten |

## Eval protocol

- Symbols: MNQ + MES, 5m Databento history (2024-01-01 → 2026-03-11).
- Discovery / holdout: first 80% / last 20% by bar count. Holdout is locked.
- Walk-forward on discovery only: train 180d, test 60d, small pre-registered grids.
- Holdout run **once** with constructor defaults (not WF winners).
- Script: `python scripts/eval_new_strategies.py`
- Tables: `reports/new_strategies/`

## Results

Evaluation artifacts are written by `scripts/eval_new_strategies.py`. See `reports/new_strategies/SUMMARY.md` for the metric table. If no module clears t ≥ 2 on walk-forward OOS **and** MES replication, the verdict is **no edge — stop**. Do not spawn EMA variants.

## Dead ends (this sprint)

- Reusing standalone `orb` / `orb_failure` / `vol_expansion_momentum` as-is: those already failed prior walk-forwards and do not flatten at RTH close.
- Overnight gap fade: excluded by the “not overnight-only” constraint (already a prior null).
- Further indicator fishing on the same 5m OHLCV set is out of scope.

## Paper only

No live connector, order router, or production config was changed.
