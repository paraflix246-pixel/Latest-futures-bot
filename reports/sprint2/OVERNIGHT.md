# Overnight report (sprint 1 + sprint 2)

Paper/backtest only. **Not live trading. No profit guarantee. No validated edge.**

## What shipped

Engineering on `cursor/mnq-ensemble-sprint1-a8b5` (PR #1), one branch:

1. **Sprint 1** — frozen MNQ 5m baseline, fill/risk realism, event-triggered router.
2. **Sprint 2** — MES replication, a priori filter/risk walk-forward, time-of-day IS scan, adaptive-engine fill parity.

No live broker code was touched. No credentials. No deploy.

## Metrics (MNQ 5m ensemble unless noted)

Account $50k, 0.5% risk, 1 tick/fill after the fix, $0.62 RT commission.
Locked holdout starts 2025-09-12. WF = 180d/60d concatenated OOS. Significant means t≥2 on ≥30 trades and positive PnL.

| Cycle | What | MNQ WF t | MNQ WF PnL | MNQ holdout | MES WF | Significant? |
|---|---|---:|---:|---:|---:|---|
| Sprint 1 before | legacy fills, level-spam breakout | -9.57 | -$48,292 | -$7,975 | n/a | no |
| Sprint 1 after | next-open fills, event-trigger, RTH, caps | **+1.76** | +$9,940 | +$1,802 | **-$5,474 (t=-1.37)** | **no** |
| Loop 2 | drop breakout from router | +1.65 | +$9,003 | +$1,471 | n/a | no |
| Sprint 2 best filter (cooldown 6 bars) | WF-selected | +1.80 | +$10,139 | +$2,003 | **-$2,946 (t=-0.73)** | **no** |
| Adaptive (realistic fills) | full history / last 90d | t=-2.23 / -1.42 | -$17,272 / -$2,590 | n/a | n/a | no |

Sprint-1 after **did not replicate on MES**. That is the honest overnight result: MNQ looked better after we stopped overtrading and filling like a fantasy; the same rules lose on MES. Do not treat MNQ after as an edge.

### Sprint 2 MNQ WF filter/risk grid (selection on WF only)

| Variant | OOS trades | OOS PnL | Green folds | t-stat |
|---|---:|---:|---:|---:|
| cooldown_6 | 426 | +10,139 | 7/10 | 1.80 |
| min_atr_gate | 440 | +10,037 | 7/10 | 1.78 |
| halt_1pct | 441 | +9,975 | 7/10 | 1.77 |
| max_contracts_5 | 441 | +7,567 | 9/10 | 1.76 |
| s1_after_baseline | 442 | +9,940 | 7/10 | 1.76 |
| atr_plus_cost | 435 | +8,971 | 7/10 | 1.63 |
| cost_frac_0.25 | 437 | +8,873 | 7/10 | 1.62 |
| skip_open_30m | 264 | -1,079 | 4/10 | -0.34 |

Cooldown-6’s t-stat bump is **+0.04** — noise. MES still loses. **Defaults stay at sprint-1 after.** Skip-open-30m hurt. No hour-of-day bucket cleared t≥2 on IS (best: 09:00 ET, t=1.58, n=189). 11:00 ET was negative (t=-2.26) on only 19 trades — not a filter.

## What changed in code

- Next-open fill, exit slippage, gap-aware stops, no same-bar re-entry, 10-contract cap
- Event-triggered Donchian/Bollinger; ensemble RTH-only; breakout does not override range
- Optional engine gates (off by default): min ATR, cost/R ≤ 0.25, skip first N minutes of RTH, engine-level RTH entries
- Adaptive engine uses the same fill/risk defaults as `run_backtest` (was still signal-close / no exit slip)

## What’s next when you wake

1. **Do not go live.** Nothing cleared t≥2, and MES failed replication.
2. Do **not** spend another sprint on 5m OHLCV pattern knobs (EMA/Donchian/VWAP/ADX grids). Two post-realism loops plus a filter grid all sat at t≈1.6–1.8 on MNQ and lost on MES.
3. Next hypothesis has to be a different information source or timeframe (daily, or a Stage-1 feature that actually survives OOS — order-book pilots already failed).
4. Optional engineering: there is **no CI** on this repo, so nothing was squash-merged. Review PR #1 and merge if the engine fixes are wanted on `main` as *infrastructure*, not as a trading go-live.
5. NQ 5m file is missing in this workspace (`DERIVED_SYMBOLS` is empty); MES was the independent instrument.

Reproduce:

```bash
python scripts/run_sprint.py --phase compare
python scripts/run_sprint2.py
python scripts/run_adaptive_research.py --symbol MNQ --timeframe 5m
```
