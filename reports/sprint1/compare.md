# Sprint 1 before/after (MNQ 5m)

Paper/backtest only. Historical simulation with modeled costs. **Not live
trading. Not a profit guarantee. t-stat &lt; 2 means we do not call this an edge.**

Account $50,000, 0.5% risk/trade, MNQ 5m, tape 2024-01-01 → 2026-03-11.
Locked holdout starts **2025-09-12** (not used to choose the fixes).
Walk-forward is 180d train / 60d test, concatenated OOS only.
Significance bar (unchanged): t-stat ≥ 2.0 on ≥ 30 OOS trades **and** positive total OOS PnL.

Fixes applied after the frozen baseline (a priori from `diagnosis.md`, not a holdout search):
event-triggered Donchian/Bollinger, no same-bar re-entry, next-open fill + exit
slippage + gap-aware stops, 10-contract cap, RTH-only ensemble, breakout does not
override a ranging regime, 3-bar cooldown, 2% daily loss halt, flatten 16:00 ET.

## Full sample

| Strategy | Phase | Trades | Win% | PF | E[$] | Net PnL | Max DD | Commission | Same-bar reentries |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| ensemble | before | 3325 | 32.0 | 0.64 | -9.29 | **-30,890** | -30,925 | 4,074 | 365 |
| ensemble | after | 633 | 36.0 | 1.22 | +13.98 | **+8,847** | -3,345 | 901 | 0 |
| trend | before | 1625 | 35.4 | 0.73 | -13.89 | -22,570 | -22,942 | 3,292 | 36 |
| trend | after | 567 | 40.0 | 1.12 | +8.48 | +4,806 | -3,842 | 774 | 0 |
| mean_reversion | before | 555 | 28.3 | 0.92 | -11.88 | -6,593 | -14,347 | 4,049 | 89 |
| mean_reversion | after | 125 | 31.0 | 1.31 | +42.03 | +5,253 | -4,134 | 463 | 0 |
| breakout | before | 3272 | 31.7 | 0.63 | -9.33 | -30,542 | -30,605 | 4,039 | 369 |
| breakout | after | 705 | 37.0 | 0.99 | -0.37 | -263 | -4,026 | 603 | 0 |

## In-sample (before 2025-09-12) vs locked holdout OOS

| Strategy | Phase | IS trades | IS PnL | OOS trades | OOS PnL | OOS PF |
|---|---|---:|---:|---:|---:|---:|
| ensemble | before | 2934 | -30,475 | 930 | **-7,975** | 0.76 |
| ensemble | after | 500 | +7,184 | 122 | **+1,802** | 1.21 |
| trend | before | 1309 | -21,143 | 395 | -4,776 | 0.81 |
| trend | after | 446 | +5,392 | 116 | -55 | 0.99 |
| mean_reversion | before | 424 | -11,918 | 132 | +7,216 | 1.34 |
| mean_reversion | after | 89 | +2,400 | 36 | +2,334 | 1.51 |
| breakout | before | 2911 | -29,329 | 878 | -7,422 | 0.74 |
| breakout | after | 582 | -1,230 | 126 | +723 | 1.15 |

Holdout OOS for the ensemble **improved** (loss → small profit). IS also improved, so this is not the classic “fit IS, die OOS” pattern. Sample on the holdout is only 122 trades.

## Walk-forward OOS (honest estimate)

| Strategy | Phase | Folds | Green folds | OOS trades | OOS PnL | Avg IS/fold | Avg OOS/fold | t-stat | Significant? |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ensemble | before | 10 | 0 | 3505 | -48,292 | -13,327 | -4,829 | **-9.57** | no |
| ensemble | after | 10 | 7 | 442 | +9,940 | +2,498 | +994 | **+1.76** | **no** |
| trend | before | 10 | 1 | 1339 | -26,161 | -7,958 | -2,616 | -4.79 | no |
| trend | after | 10 | 6 | 411 | +3,836 | +1,912 | +384 | +0.91 | no |
| mean_reversion | before | 10 | 5 | 441 | +2,043 | -1,598 | +204 | +0.19 | no |
| mean_reversion | after | 10 | 7 | 100 | +8,024 | +1,363 | +802 | +1.62 | no |
| breakout | before | 10 | 0 | 3344 | -44,520 | -12,237 | -4,452 | -10.28 | no |
| breakout | after | 10 | 4 | 508 | -1,808 | -417 | -181 | -0.75 | no |

**Readout:** OOS improved for ensemble, trend, and mean reversion after the engineering pass. **No strategy clears t ≥ 2.** We do **not** claim an edge. Breakout is still a net negative on walk-forward even after event-trigger.

## Cost stress (after engine, informational)

Same after overlays; only slippage ticks change. Not used to pick parameters.

| Config | IS PnL | Holdout OOS PnL | Full PnL |
|---|---:|---:|---:|
| ensemble 1 tick/fill (sprint default) | +7,184 | +1,802 | +8,847 |
| ensemble 2 ticks/fill | +5,708 | +1,717 | +7,263 |
| ensemble trend+MR only, 1 tick (no breakout) | +7,269 | +1,471 | +9,508 |
| mean_reversion 2 ticks/fill | +1,995 | +2,117 | +4,363 |

Sign did not flip at 2 ticks/fill on this tape. That is necessary, not sufficient.

## Loop 2 ablation (walk-forward only; holdout not used to choose)

Dropping breakout from the after-ensemble (trend+MR router, same engine overlays):

| Variant | WF OOS trades | WF OOS PnL | Green folds | t-stat |
|---|---:|---:|---:|---:|
| ensemble (breakout allowed outside range) | 442 | +9,940 | 7/10 | **1.76** |
| ensemble trend+MR only | 208 | +9,003 | 7/10 | 1.65 |

Keep breakout in the non-ranging router. It did not win the ablation, and neither variant is significant. Default stays the after-ensemble.

## Verdict

- Reproducible baseline: `reports/sprint1/before/`
- Reproducible after: `reports/sprint1/after/`
- Locked-holdout ensemble PnL: **-$7,975 → +$1,802**
- Walk-forward ensemble: **t = -9.57 → +1.76, still not significant**
- Honest label: **no validated edge yet**; overtrading and optimistic fills were real bugs, and fixing them stopped most of the bleed.

Costs: `COST_ASSUMPTIONS.md`. Diagnosis: `diagnosis.md`. Next loop: `NEXT_LOOP.md`.
