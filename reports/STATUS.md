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

Thin holdout n<30 → `PASS_*_PROVISIONAL`, not paper-live.
`READY_FOR_PAPER_LIVE_CANDIDATE` only after neighbor / bootstrap / LOYO / cost
stress on the **official** sprint-1 engine. Still hunting **both** instruments.
No `GO_LIVE_CHECKLIST`. Live stays off.

## Bottom line

| Label | Count | Notes |
|---|---:|---|
| PASS_MNQ | 0 | Official closest: `vwap_reclaim_90` WF t=1.609 n=41, HO t=2.116 n=158. Still KILL (t<2). Local `s2_orb_retrace_7` **DEMOTED** (robustness fail). Local `s4_spread_fade2` t=1.80 **fails robustness**. |
| PASS_MES | 0 official | **Local sprint-4 STRONG (soft HO):** `s2_mes_sens_7`. Official sprint-1 replay is cycle 8 — do not treat local t as PASS_MES until that replay. Prior local `filtered_orb_2` **died** on official fills. |
| PASS_BOTH | 0 | — |
| KILL | 34+ | Cycles 1–4 + 8 hunt-port families. Cycle 8 official numbers pending in this PR. |

**No paper-live. No live.**

## Local sprint 4 — MES `s2_mes_sens_7` (STRONG, soft HO)

Imported 2026-09-21. Produced **outside** this repo. Hypothesis only until
sprint-1 replay (`next_open`, exit slip, gap-aware stops, RTH flatten,
`rth_entries_only`).

| | n | t | Notes |
|---|---:|---:|---|
| Walk-forward OOS | 34 | 3.93 | Local hunt |
| Neighbor strict PASS | — | — | 42% |
| Bootstrap | — | ci_lo=1.34 | frac≥2 = 91% |
| LOYO | — | — | ok |
| Holdout | 12 | — | **THIN** — soft HO, not paper-live |

Locked params:

- `or_minutes=15`
- `entry_window_minutes=130`
- `volume_mult=1.4`
- `target_r=1.0`
- `require_vwap_align=True`
- `skip_inside_overnight=True`
- `require_retest=False`
- `stop_mode=mid`

Official port: `MesSens7Strategy` / `s2_mes_sens_7` in `src/strategies/orb_filtered.py`,
wired into `get_strategy`, `SUPPORTED_STRATEGIES`, paper harness (`PAPER_ENGINE`
= sprint-1 including `rth_entries_only`), and cycle 8.

`filtered_orb_2` (or=15 ew=120 vol=1.3) was the previous local MES provisional.
Official sprint-1 replay **KILL**: WF t=0.366 n=42, HO t=−0.854 n=55. Same-ish
n, worse t — next-open + exit-slip vs a looser fill model. ±20% sensitivity
did not recover t≥2. See `reports/cycles/harden/MES_filtered_orb_2/`.
`s2_mes_sens_7` is nearby (ew=130, vol=1.4). It **must** clear the official
engine before anyone calls it PASS_MES.

## Local sprint 3 — MNQ `s2_orb_retrace_7` DEMOTED

Do **not** promote. Local WF t=2.13 n=40 looked like PASS_MNQ_PROVISIONAL,
then failed robustness:

- neighbor strict PASS 8.3%
- bootstrap t=0.70, CI crosses 0
- LOYO 2024 lost money
- cost×2 survival is not enough

## Local sprint 4 — MNQ no strong PASS

Best near-miss: `s4_spread_fade2` WF t=1.80, **fails robustness**. Official
cycle 8 includes a small-grid `spread_fade` replay so sprint-1 numbers exist;
it is **not** a PASS candidate. New MNQ families in cycle 8:
`orb_fail_fade`, `gap_and_go`, `nr15_break`, `wick_reject_cont`,
`onh_onl_break`, `volume_dryup_break`. Cycle 7 densifies official
`vwap_reclaim_90`.

## Tape

| Symbol | Rows | UTC window | File |
|---|---:|---|---|
| MNQ 5m | 137,304 | 2024-09-22 → 2026-09-18 | `data/massive/MNQ_5m.csv.gz` |
| MES 5m | 138,366 | 2024-09-22 → 2026-09-18 | `data/massive/MES_5m.csv.gz` |

~2 years, volume-rolled. Not 2020+. Discovery before locked holdout `2025-09-12`
is ~1 year (2 WF folds at 180/60). Massive REST cannot extend pre-2024 on this
plan: 0 results. See `reports/massive/BLOCKER.md`.

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

## Cycle 3 (KILL)

| Family | MNQ n | MNQ t | MES n | MES t | Holdout MNQ t | Label |
|---|---:|---:|---:|---:|---:|---|
| orb_filtered_15 | 74 | 0.80 | 77 | −0.59 | −0.30 | KILL |
| orb_filtered_5 | 75 | −1.27 | 79 | −0.53 | −0.42 | KILL |
| orb_filtered_30 | 69 | −0.58 | 77 | −0.40 | 0.52 | KILL |
| orb_filtered_retest | 54 | 0.16 | 55 | 0.11 | 0.61 | KILL |
| orb_retrace | 41 | 0.39 | 58 | 0.45 | −0.76 | KILL |
| vwap_hour_reclaim_fail | 42 | −0.23 | 51 | −0.18 | −0.15 | KILL |
| trend15_pullback5 | 47 | 0.72 | 51 | 0.32 | 0.53 | KILL |

## Cycle 4 (KILL)

| Family | MNQ n | MNQ t | MES n | MES t | Holdout MNQ t | Label |
|---|---:|---:|---:|---:|---:|---|
| adr_exhaust_fade | 15 | 0.91 | 16 | −0.63 | 0.14 | KILL |
| gap_fill_go | 25 | 0.02 | 24 | 0.74 | 1.15 | KILL |
| morning_reversal | 21 | −1.03 | 44 | 0.15 | 0.30 | KILL |
| pdh_pdl_fail | 41 | 0.96 | 45 | 0.83 | −0.83 | KILL |
| rvol_open15 | 1 | — | 16 | 0.12 | −0.51 | KILL |
| vwap_band_fade | 35 | −0.22 | 12 | −2.05 | −1.25 | KILL |

## Cycle 6 (KILL) — official hunt port

| Family | MNQ n | MNQ t | MNQ hold t | MES n | MES t | MES hold t | Label |
|---|---:|---:|---:|---:|---:|---:|---|
| filtered_orb_2 | 8 | −0.16 | 0.43 | 42 | 0.37 | −0.85 | KILL |
| filtered_orb_90 | 6 | −0.28 | 0.23 | 37 | 0.12 | −1.45 | KILL |
| filtered_orb_5m | 1 | — | 1.50 | 40 | −0.26 | −0.36 | KILL |
| filtered_orb_adx | 7 | −0.41 | 0.28 | 30 | 0.53 | −0.17 | KILL |
| vwap_reclaim | 44 | 0.95 | 1.35 | 14 | −0.26 | −1.43 | KILL |
| **vwap_reclaim_90** | **41** | **1.61** | **2.12** | 28 | 0.57 | 0.10 | KILL |
| orb_retrace_3 | 32 | 1.25 | −0.78 | 39 | 0.40 | −1.05 | KILL |
| orb_retrace_x | 48 | −0.08 | −0.52 | 55 | −1.04 | −0.94 | KILL |

MNQ `vwap_reclaim_90`: both WF folds picked `min_away_atr=0.10`,
`stop_atr_mult=0.20`, `entry_end=11:00`, `first_hour_bias=True`.

## Cycle 7 / 8 (this PR)

- Cycle 7: densify MNQ `vwap_reclaim_90` (ADX / volume / tighter stops).
- Cycle 8: official `s2_mes_sens_7` on MES (and MNQ for completeness) plus
  new MNQ families listed above. Paper replay of MES `s2_mes_sens_7` on the
  locked holdout from `2025-09-12`. Harden after official WF.

## Extra Massive history

`reports/massive/BLOCKER.md`: 2020+ pull authenticated but **429** + **0**
pre-2024 bars on this plan. Tape stays 2024-09 → 2026-09 (two 180/60 folds).
Do not fabricate bars.

## Reproduce

```bash
python scripts/research_cycle.py --cycle 8 --symbol MES MNQ
python scripts/research_cycle.py --cycle 7 --symbol MNQ
python scripts/harden_candidate.py --family s2_mes_sens_7 --symbol MES
python scripts/run_paper_replay.py --symbol MES --timeframe 5m --strategy s2_mes_sens_7 --start 2025-09-12
python -m pytest tests/ -q
```
