# STATUS — RTH session strategies (paper / backtest only)

**Verdict: no validated edge. All five modules killed. Stop.**

This sprint added intra-session modules that are not EMA / Donchian / ADX retunes. Live trading is out of scope. Nothing here is a profit claim.

## Constraints enforced

- Primary session is RTH (09:30–16:00 America/New_York). Not overnight-only.
- Anti-cling: hard `max_hold_bars` and/or a clock exit, flatten at cash close, no averaging down, no holding losers overnight.
- Fills stay on the sprint-1 engine: signal-bar close + 1 tick; stop/target on later bars. Clock exits fill at close ± 1 tick.
- Kill rule: walk-forward OOS t-stat < 2 **or** MES fails to replicate.

## Modules

| Name | Mechanism | Exit |
|---|---|---|
| `orb_break_fade` | Combined opening-range break + failure-fade | 1.5R, broken-level / failed-extreme stop, time stop, 16:00 flatten |
| `orb_crabel` | Crabel-style ORB: RTH VWAP align, RVOL ≥ 1.5×, OR width 15–50% of prior-day ATR; fade if break fails | 1–1.5× OR height, **11:00 ET clock**, 16:00 flatten |
| `vol_squeeze_expansion` | BB-inside-Keltner + width-percentile squeeze, volume break | 1.5R, opposite BB, time stop, 16:00 flatten |
| `impulse_clock` | Large-range directional bar continuation | 1.5R, impulse extreme, max ~8 bars, 16:00 flatten |
| `last30_momentum` | First-30m RTH return → last-30m continuation (academic intra-day momentum, costs-aware) | 1R ATR stop, flatten 16:00, max 6 bars |

## Eval protocol

- Symbols: MNQ + MES, 5m (2024-01-01 → 2026-03-11).
- Split: first 80% discovery / last 20% locked holdout. Split: **2025-10-01 13:10 UTC**.
- Walk-forward on discovery only: train 180d, test 60d, 7 folds, small pre-registered grids.
- Holdout run **once** with constructor defaults (not WF winners).
- Script: `python scripts/eval_new_strategies.py`
- Tables: `reports/new_strategies/`

## Metric table

| Symbol | Strategy | WF n | WF PnL | WF t | Holdout n | Holdout PnL | Holdout t | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| MNQ | impulse_clock | 266 | +9339 | **2.42** | 93 | +5349 | **2.54** | **KILLED — MES did not replicate** |
| MES | impulse_clock | 266 | −7163 | −1.92 | 100 | −1133 | −0.51 | KILLED — WF t<2 |
| MNQ | last30_momentum | 155 | +601 | 0.36 | 29 | −1053 | −2.70 | KILLED — WF t<2 |
| MES | last30_momentum | 120 | −649 | −0.40 | 65 | −1537 | −2.35 | KILLED — WF t<2 |
| MNQ | orb_break_fade | 223 | −3185 | −0.91 | 82 | −2484 | −1.20 | KILLED — WF t<2 |
| MES | orb_break_fade | 290 | −7587 | −1.82 | 94 | +647 | 0.25 | KILLED — WF t<2 |
| MNQ | orb_crabel | 99 | −4608 | −2.04 | 53 | −1908 | −0.99 | KILLED — WF t<2 |
| MES | orb_crabel | 122 | −3444 | −1.34 | 57 | +344 | 0.15 | KILLED — WF t<2 |
| MNQ | vol_squeeze_expansion | 44 | −3305 | −2.77 | 29 | +100 | 0.10 | KILLED — WF t<2 |
| MES | vol_squeeze_expansion | 44 | −293 | −0.23 | 25 | −211 | −0.21 | KILLED — WF t<2 |

Account $50k, 0.5% risk / trade, 1-tick slippage, published commissions. Clock exits were used. Overnight holds were not part of the design.

## What looked tempting — and why it is dead

`impulse_clock` on **MNQ only** cleared t ≥ 2 on walk-forward OOS and the locked holdout. MES — the independent index — went the other way (WF t = −1.92). Single-index false positive. **Killed.**

Filtered Crabel ORB and last-30m momentum (the research-spec follow-up) both lost money on walk-forward OOS. Last-30m holdout t-stats were significantly **negative** on both symbols after costs. That matches the academic caveat that friction often kills the last-30m effect.

## Dead ends (stop here)

- Standalone `orb` / `orb_failure` / `vol_expansion_momentum`: already failed prior walk-forwards; they do not flatten at RTH close.
- Overnight gap fade: excluded by the session constraint; prior research null.
- Further EMA / Donchian / ADX / threshold fishing on this 5m OHLCV set: out of scope.
- Retail-blog ORB “playbooks” and last-30m momentum: implemented as specified, killed by the pre-registered gate.

**No edge. Not spawning variants.**

## Paper only

No live connector, order router, or production config was changed. Do not take these modules live.
