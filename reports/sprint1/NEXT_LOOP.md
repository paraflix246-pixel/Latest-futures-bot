# Next auto-loop plan (after sprint 1)

Paper/backtest only. Do not enable live trading.

Sprint 1 result to carry forward: MNQ 5m ensemble walk-forward OOS went from
t=-9.57 / -$48k to **t=+1.76 / +$9.9k**. Holdout (2025-09-12) went from
-$7,975 to +$1,802. **Fails the t≥2 significance bar.** Breakout remains
WF-negative. 2-tick cost stress did not flip the sign on this tape.

## Loop 2 (same branch, no holdout peeking for decisions)

Walk-forward ablation is done: trend+MR-only t=1.65 / +$9.0k vs ensemble-with-breakout t=1.76 / +$9.9k. **Keep breakout in the non-ranging router.** Cost-stress at 2 ticks did not flip the holdout sign.

Remaining on this branch:

1. Port next-open / exit-slip / gap-aware fills into `src/regime/adaptive_engine.py` so that path is not secretly optimistic.
2. **Do not grid-search** ADX thresholds, EMA lengths, or session hours.
3. Next *strategy* loop only if we accept a different hypothesis. If we run one more 5m OHLCV experiment and WF t is still &lt; 2: **stop this family.** Order-book Stage 1 already failed; do not revive Donchian/EMA/VWAP variants.

## Stop rule

Two consecutive post-realism loops with WF t&lt;2 and no significant OOS PnL
→ PR says **no edge yet** and we do not spend another sprint on 5m pattern
entries for MNQ.
