# Sprint 4 — fill/slippage audit

Paper/backtest only. The 1-tick MNQ 5m ensemble was **never** a validated edge
(t=1.76, MES failed). This asks whether that fragile positive *sign* is an
artifact of 1-tick fills.

| Stress | Holdout PnL | WF t | Sign gone? |
|---|---:|---:|---|
| 1 tick | +1,802 | 1.76 | no |
| 2 ticks | +1,717 | 1.61 | no |
| 4 ticks | +1,104 | 1.32 | no |
| 50% partial | +1,071 | — | no (scaled down) |
| 4 tick + gap+2 + 50% partial | +564 | 1.38 | no |

Sign does not flip on this MNQ tape. **t-stat falls. Still &lt; 2. MES already
falsified replication.** Do not read “sign survived” as “edge is robust.”

Raw JSON: `fill_audit.json`. Reproduce: `python scripts/run_sprint4.py`.
