# Next auto-loop plan (filled after sprint-1 after/compare)

This file is the handoff for the next improve-loop iteration on the same
branch. It will be completed once after-metrics land.

Do not promote anything to live trading. Paper/backtest only.

## Loop protocol (keep)

1. Freeze a locked holdout (currently 2025-09-12 → end of tape). Do not tune on it.
2. Diagnose on in-sample + walk-forward only.
3. One batch of related engineering/risk changes.
4. Re-run IS / holdout / walk-forward. Report both. No profit claims.

## Candidate next steps (priority depends on after-metrics)

1. If ensemble OOS is still a large loss: **drop breakout from the router** entirely (it dominated the before-baseline) and evaluate trend+MR only, same holdout.
2. Mean reversion was the only before-leg with non-negative WF OOS (t=0.19, not significant). Cost-stress it at 2 ticks/side and require a t-stat ≥ 2 on ≥ 30 OOS trades before calling it an edge — it almost certainly will not clear.
3. Time-of-day **expectancy table** on IS only (RTH hour buckets) for the surviving legs; promote a single hour window to holdout only if IS t-stat ≥ 2. One test, not a grid.
4. Cost-sensitivity: 0 / 1 / 2 ticks per fill on the after-engine. If the sign flips at 1 tick, there is no robust edge.
5. Engine: port the same fill/risk overlays into `src/regime/adaptive_engine.py` (still duplicates the old loop).
6. Do **not** add another 5m OHLCV pattern strategy this loop. The research dossier already retired that family.

## Stop rule

If two consecutive loops after the engine-realism pass still show walk-forward t-stat < 2 and negative total OOS PnL on MNQ 5m ensemble and its three legs, say **no edge yet** in the PR and keep iterating only on a *new information source* (session microstructure already tested, order-book already failed Stage 1) or a lower-frequency hypothesis — not more Donchian/EMA variants.
