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
| PASS_MNQ | 0 | Official engine: none yet. Local-hunt near-miss `vwap_reclaim_4` t=1.59 n=167 is being ported. |
| PASS_MES | 0 | Local hunt `filtered_orb_2` is **provisional** (WF t=2.53 n=39, holdout t=1.94 n=14 **THIN**). Not official until sprint-1 replay + sensitivity + LORO. |
| PASS_BOTH | 0 | — |
| KILL | 26 | Cycles 1–4 on official engine |

## Local hunt (imported 2026-09-21 — not yet official)

These numbers were produced **outside** this repo. They are imported here as
hypotheses to replay on the sprint-1 engine (`next_open`, exit slip, gap-aware
stops, RTH flatten). Until that replay, they are **not** PASS_MES / PASS_MNQ.

### MES provisional — `filtered_orb_2`

| | n | t | PnL |
|---|---:|---:|---:|
| Walk-forward OOS | 39 | 2.53 | +$1474 |
| Holdout | 14 | 1.94 | +$669 |

Params: `or_minutes=15`, `entry_window_minutes=120`, `volume_mult=1.3`,
`require_vwap_align=true`, `skip_inside_overnight=true`,
`require_retest=false`, `target_r=1.0`.

Holdout n=14 is **thin**. Official harden: ±20% sensitivity, leave-one-regime-out,
90/30 diagnostic WF for more OOS trades. Do not GO_LIVE on 14 holdout trades.

### MNQ KILL — local near-misses

| Variant | WF t | n | WF PnL | Holdout |
|---|---:|---:|---:|---|
| vwap_reclaim_4 | 1.59 | 167 | +$6653 | t=1.04 +$2399 |
| orb_retrace_3 | 1.48 | — | — | — |
| orb_retrace_x_1 | 1.37 | — | — | — |

MNQ push on official engine: denser grid around those three, plus MNQ-specific
tighter ATR stops, first-90-minute cutoff, ADX floor, 5-minute vs 15-minute OR.

## Tape

| Symbol | Rows | UTC window | File |
|---|---:|---|---|
| MNQ 5m | 137,304 | 2024-09-22 → 2026-09-18 | `data/massive/MNQ_5m.csv.gz` |
| MES 5m | 138,366 | 2024-09-22 → 2026-09-18 | `data/massive/MES_5m.csv.gz` |

~2 years, volume-rolled. Not 2020+. Discovery before locked holdout `2025-09-12`
is ~1 year (2 WF folds at 180/60). A Massive REST pull from 2020-01-01 is in
flight (`MASSIVE_API_KEY` present this run) to thicken samples if the plan
allows it. Failures will be written under `reports/massive/`.

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

All-day entry window (to 15:45) is why these diverged from the local hunt’s
120-minute window.

## Cycle 4 (KILL)

| Family | MNQ n | MNQ t | MES n | MES t | Holdout MNQ t | Label |
|---|---:|---:|---:|---:|---:|---|
| adr_exhaust_fade | 15 | 0.91 | 16 | −0.63 | 0.14 | KILL |
| gap_fill_go | 25 | 0.02 | 24 | 0.74 | 1.15 | KILL |
| morning_reversal | 21 | −1.03 | 44 | 0.15 | 0.30 | KILL |
| pdh_pdl_fail | 41 | 0.96 | 45 | 0.83 | −0.83 | KILL |
| rvol_open15 | 1 | — | 16 | 0.12 | −0.51 | KILL |
| vwap_band_fade | 35 | −0.22 | 12 | −2.05 | −1.25 | KILL |

## Cycle 6 (in progress) — official hunt port

`scripts/research_cycle.py --cycle 6` and `scripts/harden_candidate.py`:

- `filtered_orb_2` locked hunt params on the sprint-1 engine (MES harden + MNQ)
- MNQ denser `vwap_reclaim` / `vwap_reclaim_90` / `orb_retrace_3` / `orb_retrace_x`
- MNQ-specific: 5m OR, first-90-min, ADX, tighter ATR stops

## Reproduce

```bash
python scripts/research_cycle.py --cycle 6
python scripts/harden_candidate.py --family filtered_orb_2 --symbol MES
python scripts/harden_candidate.py --family vwap_reclaim --symbol MNQ
python -m pytest tests/ -q
```
