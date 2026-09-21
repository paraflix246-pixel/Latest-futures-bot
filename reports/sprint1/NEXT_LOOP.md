# Next auto-loop plan (after sprint 1 + loop-2 ablation)

Paper/backtest only. Do not enable live trading.

Sprint 1 result: MNQ 5m ensemble walk-forward OOS went from t=-9.57 / -$48k
to **t=+1.76 / +$9.9k**. Locked holdout (2025-09-12) went from -$7,975 to
+$1,802. **Fails the t≥2 significance bar.** 2-tick cost stress did not flip
the sign on this tape.

Loop 2 (WF only): trend+MR-only router t=1.65 / +$9.0k vs ensemble-with-breakout
t=1.76 / +$9.9k. **Keep breakout in the non-ranging router.** Neither is an edge.

## Remaining on this branch

1. Port next-open / exit-slip / gap-aware fills into
   `src/regime/adaptive_engine.py` so that path is not secretly optimistic.
2. Do **not** grid-search ADX thresholds, EMA lengths, or session hours.
3. Next *strategy* experiment only under a different hypothesis. One more
   5m OHLCV pattern variant with WF t still &lt; 2 → **stop this family.**
   Order-book Stage 1 already failed; do not revive Donchian/EMA/VWAP clones.

## Stop rule

Two consecutive post-realism loops with WF t&lt;2 → PR says **no edge yet**
and we do not spend another sprint on 5m pattern entries for MNQ. This sprint
plus the breakout ablation is that pair for the ensemble router. Remaining
work is engine-parity (adaptive path) and a genuinely new hypothesis, not
more 5m OHLCV knobs.
