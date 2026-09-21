# Sprint 3 — 15m / 1h single-strategy (not the 5m ensemble)

Paper/backtest only. Not live. No profit guarantee.

## Pre-registered hypothesis

On **15-minute and 1-hour** bars (resampled from 5m), a **single** RTH-only
strategy (trend-following *or* mean-reversion — no ensemble, no EMA/ADX/Donchian
grid) with sprint-1 realistic fills has walk-forward OOS **t ≥ 2 on MNQ** and
the **same sign on MES**.

Hard risk (unchanged): next-open fill, 1 tick/side, gap-aware stops, flatten at
16:00 ET, 2% daily loss halt, 10-contract cap, no same-bar re-entry.

## Result: **no validated edge**

| TF | Strategy | MNQ WF t | MNQ WF PnL | MNQ holdout | MES WF t | MES WF PnL | MES holdout | Clears t≥2? | MES replicates? |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| 15m | trend | **0.08** | +$187 | +$2,639 | 1.20 | +$3,254 | +$1,521 | no | no |
| 15m | mean_reversion | -1.17 | -$2,294 | -$2,075 | -0.29 | -$642 | -$1,320 | no | no |
| 1h | trend | n/a (0 WF trades) | $0 | +$148 | -1.76 | -$1,178 | +$935 | no | no |
| 1h | mean_reversion | n/a (0 WF trades) | $0 | -$999 | n/a (1 trade) | -$243 | -$940 | no | no |

Notes:

- MNQ 15m trend **holdout** looks fine (+$2.6k); **walk-forward is noise** (t=0.08). That is why the holdout is not used for selection.
- MES 15m trend is the least-bad WF (t=1.20) but MNQ does not match — not a replication.
- 1h RTH trend/MR do not produce ≥10 train trades in 180-day folds, so they fail the sample-size bar before they can fail the t-stat bar.

## Dead ends (do not re-run)

| Attempt | Why it is done |
|---|---|
| 5m ensemble (ADX router + Donchian) | Sprint 1–2: MNQ t≈1.76, **MES WF t=-1.37** |
| 5m filter/risk grid (ATR, cost/R, cooldown, halt, skip-open) | Peak MNQ t=1.80; MES still negative |
| Drop breakout from 5m ensemble | WF t=1.65, worse than keeping it |
| Adaptive expectancy router | t=-2.23 after realistic fills |
| 5m mean-reversion / trend / breakout as the ensemble legs | None cleared t≥2; breakout remains a loser |
| **15m/1h single RTH trend or MR (this sprint)** | Max MNQ WF t=0.08; 1h under-traded |
| Prior research: ORB, VWAP variants, daily Donchian, order-book Stage 1 | Already retired in `reports/RESEARCH_LOG.md` |

Do **not** spend another sprint twisting EMA lengths, ADX thresholds, or Donchian lookbacks on these tapes.

## Data / broker next steps (not more knobs)

1. **Do not go live.** Nothing cleared the t≥2 + MES-replication gate.
2. **Data:** this workspace has no NQ 5m file (`DERIVED_SYMBOLS` is empty). An independent NQ tape would be a *replication* instrument, not a new edge. Daily index data was already tested and failed ES. Order-book pilots failed Stage 1 — do not buy more of the same features.
3. **If you still want a bot path:** pick a hypothesis that is **not** OHLCV pattern-matching on MNQ/MES 5m–1h (for example: a defined paper-trade process to *audit fills* against the next-open + 1-tick model, or a different asset class). That is operations/research design, not a parameter sweep.
4. **Broker:** keep Rithmic/MT5/TradersPost **off**. Paper-orders with fill-quality logging are the only broker-adjacent step that is still honest. No credentials, no live deploy.

Reproduce: `python scripts/run_sprint3.py`
