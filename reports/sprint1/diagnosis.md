# Sprint 1 diagnosis (from the frozen **before** baseline)

Paper/backtest only. Historical simulation, not live results.

MNQ 5m, $50k, 0.5% risk, legacy engine (signal-close fill, 1-tick **entry** slippage only, $0.62 RT commission). Full sample 2024-01-01 → 2026-03-11. Locked holdout starts 2025-09-12.

## Headline

The 5m ensemble is not an overfit winner that dies out of sample. It **loses in-sample and out-of-sample**. It is almost the same strategy as raw Donchian breakout. Overnight Globex supplies most of the trades. Costs make a bad underlying worse; they are not the whole story.

## Metrics (before)

| Split | Strategy | Trades | Win% | PF | Expectancy | Net PnL | Max DD |
|---|---|---:|---:|---:|---:|---:|---:|
| Full | ensemble | 3325 | 32.0 | 0.64 | -$9.29 | -$30,890 | -$30,925 |
| Full | breakout | 3272 | 31.7 | 0.63 | -$9.33 | -$30,542 | -$30,605 |
| Full | trend | 1625 | 35.4 | 0.73 | -$13.89 | -$22,570 | -$22,942 |
| Full | mean_reversion | 555 | 28.3 | 0.92 | -$11.88 | -$6,593 | -$14,347 |
| IS (<2025-09-12) | ensemble | 2934 | — | — | — | -$30,475 | — |
| Holdout OOS | ensemble | 930 | — | — | — | -$7,975 | — |
| Holdout OOS | mean_reversion | 132 | — | — | — | **+$7,216** | — |
| WF OOS | ensemble | 3505 | 32.1 | — | t=-9.57 | -$48,292 | 0/10 folds green |
| WF OOS | mean_reversion | 441 | 29.6 | — | t=+0.19 | +$2,043 | 5/10 folds green |

Walk-forward for ensemble matches the previously saved `reports/walk_forward/MNQ_ensemble.json` (same -$48,291.59 OOS). Mean-reversion's holdout profit is **not** a validated edge: walk-forward t-stat 0.19, in-sample was -$11.9k (the opposite of classic overfit, i.e. a lucky OOS window).

## Overfit

- Ensemble IS and OOS are both large losses. This is **no-edge**, not an IS-only curve fit.
- Ensemble has no parameter grid in walk-forward (`best_params: {}`), so there is nothing to overfit at the search layer. The damage is the signal itself plus the engine.

## Trade count / overtrading

- Breakout **level** signals: 8,890 bars with a direction; 2,225 of those are "still beyond the Donchian," not a new break. Event-trigger is the first fix.
- Ensemble executed 3,325 trades in ~800 calendar days (~4/day). Median hold **25 minutes**. Exit reasons: 3,243 trail / 53 stop / 29 target — i.e. the router is a trailing-stop breakout machine.
- **365 same-bar re-entries** (exit and enter on the same timestamp). Engine bug.

## Fill realism

- Entry at signal close + 1 tick is optimistic versus next-open fill.
- **No exit slippage.** Stops fill at the stop even when the bar gaps through it.
- Same-bar trail tighten then low-hits-new-stop is an OHLC-path fantasy.
- Commission on the ensemble full sample: **$4,074** of a **$26,816** gross loss. The strategy loses before costs; costs add ~13% of the damage.
- Mean reversion is the cost-sensitive leg: gross -$2,545 vs commission -$4,049. High turnover + $0.62 RT on a small target (mid band) cannot survive.

## Session

- RTH (09:30–16:00 ET) ensemble entries: 441, PnL -$6,973 (~-$15.8/trade)
- Non-RTH: 2,884, PnL -$23,917 (~-$8.3/trade)
- Cutting overnight **reduces total bleed** even though per-trade RTH is worse. That is a risk/activity cut, not an edge claim. Combined with flatten-at-close it also removes overnight gap fiction.

## Highest-leverage fixes chosen (a priori from this diagnosis, not from holdout search)

1. Event-trigger Donchian / Bollinger (stop level-spam).
2. Ensemble: do not let breakout override a ranging regime (restore the ADX router).
3. No same-bar re-entry; 3-bar cooldown.
4. Next-open fill, exit slippage, gap-aware stops, next-bar trail.
5. Max 10 contracts.
6. RTH-only ensemble entries + flatten at 16:00 ET.
7. 2% daily loss halt on new entries.

If after these the locked holdout and walk-forward OOS are still negative with t-stat < 2, the honest readout is still **no edge** — with a more realistic engine and less self-inflicted turnover.

## After (same splits, realistic engine + event-trigger + RTH ensemble)

| Split | Strategy | Trades | PF | Net PnL | vs before |
|---|---|---:|---:|---:|---|
| Full | ensemble | 633 | 1.22 | +$8,847 | was -$30,890 |
| Holdout OOS | ensemble | 122 | 1.21 | +$1,802 | was -$7,975 |
| WF OOS | ensemble | 442 | — | +$9,940 (t=+1.76, 7/10 folds) | was -$48,292 (t=-9.57, 0/10) |
| WF OOS | mean_reversion | 100 | — | +$8,024 (t=+1.62) | was +$2,043 (t=+0.19) |
| WF OOS | breakout | 508 | — | -$1,808 (t=-0.75) | was -$44,520 (t=-10.28) |

Same-bar re-entries: 365 → 0. Commission on ensemble full sample: $4,074 → $901.

**We do not call this an edge.** t=1.76 is below the project's bar of 2.0. The sign is better because we stopped overtrading a negative-expectancy breakout and stopped filling like a fantasy. See `compare.md`.
