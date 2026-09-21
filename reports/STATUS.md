# Status — founder wake-up

Paper/backtest only. **Not live trading. No profit guarantee. No validated edge.**

PR: https://github.com/paraflix246-pixel/Latest-futures-bot/pull/1  
Branch: `cursor/mnq-ensemble-sprint1-a8b5`  
No GitHub CI — **not auto-merged**.

## Bottom line

Four overnight sprints. The 5m OHLCV ensemble on MNQ can be made to look less bad by fixing engine bugs and filling more honestly. **It does not clear t≥2, and it loses on MES.** 15m/1h single strategies also fail. Harsher fills (2–4 ticks, partials) shrink the MNQ number; they do not create an edge, and they do not need to “erase” one that was never validated.

**Do not go live. Do not retune EMA / Donchian / ADX.**

## What is actually true

| Sprint | Question | Answer |
|---|---|---|
| 1 | Baseline MNQ 5m ensemble | Legacy engine: WF t=-9.57, -$48k OOS. After realistic fills + event-trigger + RTH: WF t=**+1.76**, holdout +$1,802. **Not significant.** |
| 2 | Does it replicate? Filters? | **MES WF t=-1.37.** Filter grid peak t=1.80, MES still negative. Adaptive t=-2.23. |
| 3 | 15m/1h single RTH trend or MR | MNQ 15m trend WF t=**0.08**. MR negative. 1h under-traded. **No.** |
| 4 | Does the 1-tick MNQ number survive harsher fills? | Sign stays positive on MNQ through 4 ticks (WF t 1.76→1.31; holdout +$1,802→+$1,104). Partial 50% ≈ halves PnL. Harsh combo still +$564 holdout, t=1.38. **Still not an edge. MES already failed.** |

### Sprint 4 fill audit (MNQ 5m ensemble, sprint-1 after rules)

| Fill stress | Holdout PnL | WF PnL | WF t | Significant? |
|---|---:|---:|---:|---|
| 1 tick/side (research default) | +1,802 | +9,940 | 1.76 | no |
| 2 ticks | +1,717 | +9,044 | 1.61 | no |
| 3 ticks | +1,342 | — | — | no |
| 4 ticks | +1,104 | +7,265 | 1.32 | no |
| 1 tick + 2 extra ticks on gapped stops | +1,800 | — | — | no |
| 1 tick + 50% partial fill | +1,071 | — | — | no |
| 4 ticks + gap extra 2 + 50% partial | +564 | +3,512 | 1.38 | no |

The 1-tick model is **optimistic relative to 2–4 ticks**, but the MNQ positive sign is not a 1-tick artifact alone. The **replication failure on MES** is the binding constraint. Gap extra barely moved this tape (few gap-throughs). Partial fills scale size down; they do not magically create significance.

## Dead ends — do NOT try next

Do not spend another cycle on:

- EMA lengths, ADX thresholds, Donchian lookbacks
- 5m ensemble voting / “add another leg”
- Skip-open-30m, session-hour fishing from the IS table
- VWAP / ORB / daily Donchian / order-book features already retired in `reports/RESEARCH_LOG.md`
- Calling holdout PnL an edge when walk-forward t&lt;2 (15m trend holdout +$2.6k vs WF t=0.08)

## Infrastructure that is real

- Realistic engine: next-open fill, exit slippage, gap-aware stops, no same-bar re-entry, contract cap.
- Optional stress knobs: `slippage_ticks`, `gap_extra_ticks`, `fill_fraction`.
- Paper replay (no broker): `python scripts/run_paper_replay.py --symbol MNQ --timeframe 5m --strategy ensemble --start 2025-09-12`  
  `live=True` raises. Sample log: `reports/paper/MNQ_5m_ensemble_replay.json`.
- Reproduce research: `run_sprint.py --phase compare`, `run_sprint2.py`, `run_sprint3.py`, `run_sprint4.py`.

## Recommended next REAL hypothesis

Not another OHLCV pattern on this 2024–2026 MNQ/MES 5m–1h tape.

1. **Fill-model validation (highest-leverage ops):** run the paper harness vs a *paper* (not live) broker blotter for a few RTH sessions and compare actual micro fills to 1 vs 2 vs 4 ticks. That tests the cost assumption, not a new signal. No live credentials.
2. **Different information:** if you buy data, buy something that is not another month of MBP-1 `persistence` / imbalance (Stage 1 already failed). A longer *independent* instrument (ES daily was already a fail) or a non-index product is a new hypothesis; more years of the *same* MNQ 5m patterns is not.
3. **Accept “no bot yet.”** A capable bot is not the same as a fitted 5m ensemble. The engine is now honest enough that further pattern-mining on this tape is the wrong spend.

## What to merge

Merge PR #1 only if you want the **engine + paper harness + reports** on `main`. That is infrastructure. It is not a trading go-ahead.
