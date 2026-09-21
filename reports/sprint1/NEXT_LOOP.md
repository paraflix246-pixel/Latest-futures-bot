# Next auto-loop plan (after overnight sprint 2)

Paper/backtest only. Do not enable live trading.

**Stop the 5m OHLCV ensemble family.** MNQ sprint-1 after is t=1.76 and fails MES replication (WF t=-1.37). Filter/risk grid peaked at t=1.80 with MES still negative. Adaptive with realistic fills: t=-2.23.

## When the founder wakes

- Review PR #1 as **engine/risk infrastructure**, not a profitable bot.
- Merge only if you want next-open fills and event-triggers on `main`.
- Next research: a different hypothesis (not another 5m Donchian/EMA/ADX knob).
