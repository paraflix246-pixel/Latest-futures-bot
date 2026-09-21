# Status — Massive tape research

Paper/backtest only. **Not live trading. No profit guarantee. No validated edge.**

PR: https://github.com/paraflix246-pixel/Latest-futures-bot/pull/3
Branch: `cursor/massive-long-tape-research-6b77`

## Gate (founder 2026-09-21 — twin-strategy rule rescinded)

A strategy that works is the goal. **MNQ-only is acceptable** if it clears the
rigorous gate. MES does **not** need the same logic or params.

| Label | Meaning |
|---|---|
| **PASS_MNQ** | MNQ walk-forward OOS t ≥ 2.0, n ≥ 30, holdout t ≥ −1.0, sprint-1 fills, RTH/hard exits, no overnight cling. Document as MNQ-only candidate. Founder will trade only MNQ. |
| **PASS_MES** | Same bar on MES with its own params/strategy. |
| **PASS_BOTH** | Bonus if both clear (same or different strategies). |
| **KILL** | In-sample only wins, overnight cling, live trading, fabricated data, or WF/holdout miss. |

Still hunting **both** instruments in parallel. No `GO_LIVE_CHECKLIST`. Live stays off.

## Bottom line

| Label | Count | Notes |
|---|---:|---|
| PASS_MNQ | 0 | None yet |
| PASS_MES | 0 | None yet |
| PASS_BOTH | 0 | — |
| KILL | 13 | Cycles 1–2 (cycle-3 ORB/VWAP/retrace running) |

Closest historical MNQ print remains `on_inventory` (cycle 1, t=1.01, n=23 — under-traded, **KILL**).

Cycle 3 (filtered ORB 5/15/30/retest, ORB retrace, first-hour VWAP reclaim/fail, 15m-trend+5m-pullback) is next on the Massive tape. Cycle 4 (gap fill/go, opening rvol, VWAP-band fade, ADR exhaustion, PDH/PDL fail, morning reversal) is wired and will run if cycle 3 has no PASS_MNQ.

## Tape

| Symbol | Rows | UTC window | File |
|---|---:|---|---|
| MNQ 5m | 137,304 | 2024-09-22 → 2026-09-18 | `data/massive/MNQ_5m.csv.gz` |
| MES 5m | 138,366 | 2024-09-22 → 2026-09-18 | `data/massive/MES_5m.csv.gz` |

~2 years, volume-rolled. Not 2020+. Discovery before locked holdout `2025-09-12` is ~1 year (2 WF folds at 180/60).

## Cycle 1 (KILL)

| Family | MNQ n | MNQ t | MES n | MES t | Holdout MNQ t | Label |
|---|---:|---:|---:|---:|---:|---|
| ensemble | 72 | −0.96 | 104 | −1.76 | 1.30 | KILL |
| orb_crabel | 20 | −1.08 | 30 | −1.37 | 0.80 | KILL |
| last30_momentum | 42 | −0.90 | 16 | −0.54 | −1.41 | KILL |
| vol_squeeze_expansion | 14 | −2.44 | 14 | −0.40 | 0.14 | KILL |
| impulse_clock | 74 | −0.35 | 71 | −1.55 | 1.48 | KILL |
| vol_gated_ensemble | 9 | −0.17 | 35 | 0.50 | 1.54 | KILL |
| ib_extension | 16 | −1.35 | 48 | −0.36 | 0.10 | KILL |
| on_inventory | 23 | 1.01 | 28 | −0.72 | −0.09 | KILL |
| lunch_range_break | 7 | −0.13 | 24 | −0.51 | 1.30 | KILL |

## Cycle 2 (KILL)

| Family | MNQ n | MNQ t | MES n | MES t | Holdout MNQ t | Label |
|---|---:|---:|---:|---:|---:|---|
| afternoon_momentum | 25 | −0.52 | 33 | −1.05 | −0.15 | KILL |
| am_vwap_reclaim | 48 | −1.49 | 61 | 0.44 | −1.88 | KILL |
| failed_ib_fade | 61 | −2.26 | 58 | 0.85 | −0.91 | KILL |
| open_drive | 28 | −0.68 | 35 | −1.71 | 0.11 | KILL |

## Reproduce

```bash
python scripts/research_cycle.py --cycle 3
python scripts/research_cycle.py --cycle 4
python -m pytest tests/ -q
```
