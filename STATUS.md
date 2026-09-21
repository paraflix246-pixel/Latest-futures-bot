# STATUS — RTH session strategies (paper / backtest only)

**Verdict: no validated edge. All three modules killed. Stop.**

This sprint added three **new** intra-session modules. They are not EMA / Donchian / ADX retunes. Live trading is out of scope. Nothing here is a profit claim.

## Constraints enforced

- Primary session is RTH (09:30–16:00 America/New_York). Not overnight-only.
- Anti-cling: hard `max_hold_bars`, flatten at cash close (`rth_flatten`), no averaging down (engine stays one position), no holding losers overnight.
- Fills stay on the sprint-1 engine: signal-bar close + 1 tick; stop/target on later bars. Clock exits fill at close ± 1 tick.
- Kill rule: walk-forward OOS t-stat < 2 **or** MES fails to replicate.

## Modules

| Name | Mechanism | Exit |
|---|---|---|
| `orb_break_fade` | Combined opening-range break + failure-fade state machine | 1.5R target, stop at broken level / failed extreme, time stop, 16:00 flatten |
| `vol_squeeze_expansion` | BB-inside-Keltner + width-percentile squeeze, volume break | 1.5R, opposite BB, time stop, 16:00 flatten |
| `impulse_clock` | Large-range directional bar continuation | 1.5R, impulse extreme, max 8 bars default, 16:00 flatten |

## Eval protocol

- Symbols: MNQ + MES, 5m (2024-01-01 → 2026-03-11).
- Split: first 80% discovery / last 20% locked holdout. Split timestamp: **2025-10-01 13:10 UTC**.
- Walk-forward on discovery only: train 180d, test 60d, 7 folds, small pre-registered grids.
- Holdout run **once** with constructor defaults (not WF winners).
- Script: `python scripts/eval_new_strategies.py`
- Tables: `reports/new_strategies/`

## Metric table

| Symbol | Strategy | WF n | WF PnL | WF t | WF sig | Holdout n | Holdout PnL | Holdout t | Verdict |
|---|---|---:|---:|---:|---|---:|---:|---:|---|
| MNQ | impulse_clock | 266 | +9338.94 | **2.418** | yes | 93 | +5349.16 | **2.542** | **KILLED — MES did not replicate** |
| MES | impulse_clock | 266 | −7163.37 | −1.915 | no | 100 | −1133.11 | −0.507 | KILLED — WF t<2 |
| MNQ | orb_break_fade | 223 | −3185.47 | −0.906 | no | 82 | −2484.41 | −1.195 | KILLED — WF t<2 |
| MES | orb_break_fade | 290 | −7586.64 | −1.823 | no | 94 | +647.36 | 0.252 | KILLED — WF t<2 |
| MNQ | vol_squeeze_expansion | 44 | −3304.65 | −2.771 | no | 29 | +100.19 | 0.098 | KILLED — WF t<2 |
| MES | vol_squeeze_expansion | 44 | −293.07 | −0.234 | no | 25 | −211.10 | −0.212 | KILLED — WF t<2 |

Account $50k, 0.5% risk / trade, 1-tick slippage, published commissions. Clock exits were used (time_stop / rth_flatten / stop / target). `held_past_rth_close` was 0 on five of six holdouts; MES `orb_break_fade` had 1/94 exits after 16:05 ET (data-gap / slice-end, not a designed overnight hold).

## What looked tempting — and why it is dead

`impulse_clock` on **MNQ only** cleared t ≥ 2 on both walk-forward OOS and the locked holdout (6/7 profitable WF folds; holdout win rate 60%, PF 1.79). MES — the independent index — went the other way: WF t = −1.92, holdout t = −0.51, 1/7 profitable folds. That is a single-index false positive, not an edge. The pre-registered MES replication rule exists exactly for this. **Killed. Do not promote.**

The other two modules never cleared t = 2 on either symbol.

## Dead ends (stop here)

- Reusing standalone `orb` / `orb_failure` / `vol_expansion_momentum`: already failed prior walk-forwards; they do not flatten at RTH close.
- Overnight gap fade: excluded by the session constraint; prior research null.
- Further EMA / Donchian / ADX / threshold fishing on this same 5m OHLCV set: out of scope. No edge found; not spawning variants.

## Paper only

No live connector, order router, or production config was changed. Do not take these modules live.
