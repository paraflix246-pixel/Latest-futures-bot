# Status — Massive tape research

Paper/backtest only. **Not live trading. No profit guarantee.** Statistical
**PASS_MES** on `gap_on_confirm_lock`; holdout expectancy is slightly negative
so this is **not** a paper-live candidate.

PR: https://github.com/paraflix246-pixel/Latest-futures-bot/pull/3
Branch: `cursor/massive-long-tape-research-6b77`

## Gate (founder 2026-09-21 — twin-strategy rule rescinded)

A strategy that works is the goal. **MNQ-only is acceptable** if it clears the
rigorous gate. MES does **not** need the same logic or params.

| Label | Meaning |
|---|---|
| **PASS_MNQ** | MNQ walk-forward OOS t ≥ 2.0, n ≥ 30, holdout t ≥ −1.0, sprint-1 fills, RTH/hard exits, no overnight cling. |
| **PASS_MES** | Same bar on MES with its own params/strategy. |
| **PASS_BOTH** | Bonus if both clear (same or different strategies). |
| **KILL** | In-sample only wins, overnight cling, live trading, fabricated data, or WF/holdout miss. |

Thin holdout n<30 → `PASS_*_PROVISIONAL`, not paper-live.
`READY_FOR_PAPER_LIVE_CANDIDATE` only after neighbor / bootstrap / LOYO / cost
stress on the **official** sprint-1 engine. No `GO_LIVE_CHECKLIST`. Live stays off.

## Bottom line

| Label | Count | Notes |
|---|---:|---|
| PASS_MNQ | **1** | **1m** `vwap_reclaim_90_lock` (`min_away_atr=0.10`, `stop_atr_mult=0.30`, 11:00, first-hour bias). WF t=**3.943** n=259 (7/7 folds), HO t=**3.696** n=87 +$4893, overnight=0. Neighbors 5/5, cost×2 t=3.78, bootstrap CI lo=1.61. **READY_FOR_PAPER_LIVE_CANDIDATE. No live.** |
| PASS_MES | **1** | 5m `gap_on_confirm_lock` (`confirm_atr=0.12`, `stop_atr_mult=0.25`). WF t=3.656 n=36, HO t=−0.166 n=140. **Not paper-live.** |
| PASS_BOTH | 0 | Independent symbols/tapes. MES 1m of the MNQ lock not yet run. |
| KILL | 74+ | Cycles 1–4, 6–13, 15–17. Cycle 18 MES lock on MNQ 1m KILL. Grid-first stop=0.20 lock WF t=1.847. |

**PASS_MNQ READY_FOR_PAPER_LIVE_CANDIDATE (1m VWAP reclaim lock). PASS_MES statistical only. No live.**

`MASSIVE_API_KEY` **is present** (`os.environ` only, never printed). Live plan-depth: earliest bar **2024-09-23**. Founder: **2024–now is the working tape** — do not wait for a plan upgrade. MNQ hunt continues here.

## PR #2 squash-merge

Squash-landed on `main` as `84c509a` (2026-09-21). Toolkit only: five RTH
modules, eval harness, `reports/new_strategies/` kill tables, and clock
exits on the sprint-1 next-open engine. Sprint reports / paper harness
kept. The five families remain **killed** (no validated edge). PR #2 is
closed. Hunt continues on this branch (PR #3).

## Massive plan depth (live, key present)

See `reports/massive/PLAN_DEPTH.md` and `BLOCKER.md`. Auth Bearer 200. Earliest `MNQZ4` session 2024-09-23. Do not fabricate bars.

## Local sprint 4 vs official engine — MES `s2_mes_sens_7`

Locked params: `or=15`, `ew=130`, `vol=1.4`, `R=1.0`, VWAP align, skip inside overnight, stop=mid.

| Source | n | t | PnL |
|---|---:|---:|---:|
| Local hunt WF | 34 | **3.93** | — |
| Local neighbor strict PASS | — | 42% | boot ci_lo=1.34, frac≥2 91%, LOYO ok |
| Local holdout | 12 | — | **THIN** (soft HO) |
| **Official WF 180/60** | **39** | **0.414** | +$535 |
| **Official holdout** | **41** | **−0.073** | **−$88** |
| Paper replay (holdout, sprint-1 engine) | 41 | — | −$88, WR 51%, PF 0.98 |
| Diagnostic 90/30 WF (not the gate) | 65 | 1.022 | still <2 |
| Best ±20% neighbor (`volume_mult=1.12`) | 46 | 1.12 | HO t=−1.555 **worse** |

Port: `MesSens7Strategy` / `s2_mes_sens_7`, `get_strategy`, paper harness
(`PAPER_ENGINE` = `SPRINT1_AFTER_ENGINE` including `rth_entries_only`).
Harden: `reports/cycles/harden/MES_s2_mes_sens_7/`.
Paper log: `reports/paper/MES_5m_s2_mes_sens_7_replay.json`.

Nearby `filtered_orb_2` (ew=120, vol=1.3) already died on official fills
(WF t=0.366 n=42, HO t=−0.854). `s2_mes_sens_7` is the same family with a
slightly longer window and stricter volume. Sprint-1 fills eat the local t.

## Local sprint 3 — MNQ `s2_orb_retrace_7` DEMOTED

Do **not** promote. Local WF t=2.13 n=40 looked like PASS_MNQ_PROVISIONAL,
then failed robustness: neighbor strict PASS 8.3%, bootstrap t=0.70 CI
crosses 0, LOYO 2024 lost money. Cost×2 survival is not enough.

## Local sprint 4 — MNQ no strong PASS

Best local near-miss `s4_spread_fade2` WF t=1.80, **fails robustness**.
Official `spread_fade` WF t=0.997 n=52, HO t=0.909 n=167 — KILL.

## Tape

| Symbol | Rows | UTC window | File |
|---|---:|---|---|
| MNQ 5m | 137,304 | 2024-09-22 → 2026-09-18 | `data/massive/MNQ_5m.csv.gz` |
| MES 5m | 138,366 | 2024-09-22 → 2026-09-18 | `data/massive/MES_5m.csv.gz` |

Massive REST cannot extend pre-2024 on this plan: **0 results**.
See `reports/massive/BLOCKER.md`. Discovery before `2025-09-12` is two
180/60 folds. Do not fabricate bars.

## Cycle 1–4 (KILL)

See earlier tables. 26 families. None near t=2.

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

## Cycle 7 (KILL) — densify MNQ `vwap_reclaim_90`

| Family | MNQ n | MNQ t | MNQ hold t | Label |
|---|---:|---:|---:|---|
| vwap_reclaim_90_dense | 45 | 1.357 | 1.391 | KILL |
| vwap_reclaim_90_adx | 37 | 0.656 | 2.116 | KILL |
| **vwap_reclaim_90_vol** | **41** | **1.609** | **2.116** | KILL (same as cycle 6) |
| orb_retrace_3_dense | 29 | −0.205 | −0.913 | KILL |

Tighter stops / ADX / volume did not lift WF t above 1.61.

## Cycle 8 (KILL) — MES winner + new MNQ families

| Family | MNQ n | MNQ t | MNQ hold t | MES n | MES t | MES hold t | Label |
|---|---:|---:|---:|---:|---:|---:|---|
| **s2_mes_sens_7** | 4 | 0.008 | 0.558 | **39** | **0.414** | **−0.073** | KILL |
| orb_fail_fade | 32 | 0.59 | 2.224 | 38 | −0.013 | −0.007 | KILL |
| gap_and_go | 10 | −2.008 | −0.189 | 10 | −6.077 | −1.63 | KILL |
| nr15_break | 58 | 1.044 | −0.309 | 74 | 0.359 | −2.196 | KILL |
| wick_reject_cont | 44 | −0.497 | 0.823 | 44 | −0.458 | 1.099 | KILL |
| onh_onl_break | 17 | 0.447 | 0.51 | 48 | 0.028 | 0.736 | KILL |
| volume_dryup_break | 50 | −1.447 | −0.327 | 69 | −0.362 | −0.586 | KILL |
| spread_fade | 52 | 0.997 | 0.909 | 46 | −1.182 | −0.863 | KILL |

MNQ `nr15_break` 2/2 profitable folds, t=1.04 — not a PASS.
MNQ `orb_fail_fade` holdout t=2.22 but WF t=0.59 — not a PASS.

## Cycle 9 (KILL) — more MNQ inventions

| Family | MNQ n | MNQ t | MNQ hold t | MES n | MES t | MES hold t | Label |
|---|---:|---:|---:|---:|---:|---:|---|
| ib_hold_break | 37 | −0.936 | 0.903 | 66 | 0.094 | 0.364 | KILL |
| inside_hour_break | 2 | 0.08 | 0.261 | 35 | −1.217 | −0.654 | KILL |
| higher_low_vwap | 33 | −1.035 | 0.386 | 25 | 1.394 | −1.574 | KILL |
| prior_mid_reclaim | 13 | −0.633 | −0.551 | 18 | 0.447 | −0.173 | KILL |

## Cycle 10 (KILL) — more MNQ inventions + vwap_reclaim_90 target grid

| Family | MNQ n | MNQ t | MNQ hold t | MES n | MES t | MES hold t | Label |
|---|---:|---:|---:|---:|---:|---:|---|
| vwap_reclaim_90_target | 41 | 1.546 | 1.572 | 27 | 0.902 | −0.49 | KILL |
| morning_range_break | 17 | −0.123 | 0.90 | 54 | −0.057 | 0.391 | KILL |
| keltner_am_fade | 45 | 1.122 | −0.206 | 70 | −2.963 | −1.045 | KILL |
| inside_day_orb | 2 | −4.65 | 0.894 | 3 | −0.561 | −0.579 | KILL |
| pivot_bounce | 32 | 0.311 | −0.817 | 39 | 1.339 | −0.898 | KILL |

Target_r / one_per_session around the 1.61 neighborhood did not lift WF t. MES `pivot_bounce` 2/2 folds but holdout negative.

## Cycle 11 (KILL) — MNQ 15m resample

Same families on 15-minute bars (resampled from 5m). **0 WF trades** (train never cleared min_train_trades). Not a PASS.

## Cycle 12 (KILL) — improved founder ideas on 2y tape

Prior cycle 3/4 kills already re-evaled on this Massive 2y tape. Cycle 12
used *improved* classifiers, not identical grids. All **KILL**. EMA/Donchian
regime pockets: **LEAVE_DEAD** (no year/ADX/ATR pocket with t≥2 n≥30).

| Family | MNQ n | MNQ t | MNQ hold t | MES n | MES t | MES hold t | Label |
|---|---:|---:|---:|---|---:|---:|---|
| vwap_fh_reclaim | 38 | −1.288 | −1.417 | 62 | −0.373 | −1.933 | KILL |
| gap_on_range | 46 | 0.15 | −1.405 | 45 | 1.213 | −0.285 | KILL |
| rvol_dir_open15 | 14 | −2.282 | −1.216 | 19 | −0.274 | 0.581 | KILL |
| trend15_pb5_chop | 41 | 0.101 | −1.328 | 68 | −1.374 | 0.662 | KILL |

MES `gap_on_range` 2/2 profitable folds, t=1.213 — not a PASS. First-hour-during
VWAP and loosened RVOL are worse than the already-killed after-10:30 / tight-RVOL
versions. ADX chop skip did not lift the 15m/5m family.

See `reports/cycles/cycle_12/` and `REGIME_POCKETS.md`.

## Cycle 13 (KILL) — open reject / confirmed ON-range / measured move / VWAP hold

| Family | MNQ n | MNQ t | MNQ hold t | MES n | MES t | MES hold t | Label |
|---|---:|---:|---:|---|---:|---:|---|
| open_reject | 30 | −0.602 | −1.799 | 39 | −3.168 | −3.84 | KILL |
| gap_on_confirm | 28 | −1.507 | −1.002 | **36** | **3.656** | **−1.594** | KILL (HO) |
| am_measured | 36 | 0.382 | −1.193 | 38 | −1.095 | −0.494 | KILL |
| vwap_hold_late | 49 | −0.501 | −0.5 | 67 | 0.216 | −1.287 | KILL |

MES `gap_on_confirm` is the first official WF t≥2 print this hunt: both discovery
folds picked `confirm_atr=0.12`, `stop_atr_mult=0.25`, pooled OOS t=3.656 n=36.
Holdout uses constructor-grid *first* values (`confirm_atr=0.05`) and is
strongly negative (t=−1.594) → **KILL**, not PASS_MES. Do not promote. Cycle 14
locks those discovery fold-consensus defaults and re-holdouts once.

## Cycle 14 — PASS_MES `gap_on_confirm_lock`

Locked from cycle-13 discovery fold consensus (both folds): `confirm_atr=0.12`,
`stop_atr_mult=0.25`. Sprint-1 fills. RTH. Flatten 15:45. Overnight cling=0.

| Source | n | t | PnL |
|---|---:|---:|---|
| Official WF 180/60 | **36** | **3.656** | +$3411 |
| Official holdout (2025-09-12) | **140** | **−0.166** | **−$309** |
| Paper replay (holdout) | 140 | — | −$309, WR 50.7%, PF 0.96 |
| Diagnostic 90/30 WF (not the gate) | 84 | 1.846 | still <2 |
| ±20% neighbors | 5/5 | all t≥2.5 | all HO t≥−0.62 **PASS_MES** |

Gate: **PASS_MES**. Holdout is *not* strongly negative, n≥30, no overnight.
Holdout expectancy is slightly negative — this is a statistical pass, not an
economic one. Diagnostic 90/30 t=1.846 and LORO remaining t=0.596 if 2025Q2
is dropped. **Not** `READY_FOR_PAPER_LIVE_CANDIDATE`. No bootstrap/cost×2 yet.
MNQ same lock: WF t=−1.699 n=28 KILL.

See `reports/cycles/cycle_14/` and `reports/cycles/harden/MES_gap_on_confirm_lock/`.
Paper log: `reports/paper/MES_5m_gap_on_confirm_replay.json`.

## Cycle 15 (KILL) — fill-only / cross-lead / weekday clock / vol-clock

2024–now 5m tape. Clock vs bars diagnostic on MNQ discovery: **NOT_IN_CLOCK_OR_BARS_YET**.

| Family | MNQ n | MNQ t | MNQ hold t | MES n | MES t | MES hold t | Label |
|---|---:|---:|---:|---|---:|---:|---|
| gap_on_fill_only | 25 | −1.157 | −0.904 | 25 | **2.679** | −0.724 | KILL (n<30) |
| cross_lead_open15 | 43 | −1.515 | −1.075 | 44 | −0.513 | −1.518 | KILL |
| weekday_gap_clock | 19 | −1.219 | −0.264 | 29 | −1.021 | −0.907 | KILL |
| vol_clock_fade | 2 | 0.258 | −0.397 | 34 | −0.91 | −1.601 | KILL |

MES fill-only is the same family as PASS_MES without the go-leg: t≥2 but **n=25** so it is not even PASS_MES_PROVISIONAL (gate is WF n≥30). MNQ of that family stays negative. Weekday/clock and volume-clock do not clear. Always-long/short RTH baselines: clock_short t=0.688, clock_long t=−0.971 — not a calendar edge.

See `reports/cycles/cycle_15/` and `BAR_VS_CLOCK.md`. Hunt continues (cycle 16: go-only, fade overnight gap, fade first-30m, lunch OR magnet).

## Cycle 16 (KILL) — go-only / fade overnight gap / first-30m fade / lunch magnet

| Family | MNQ n | MNQ t | MNQ hold t | MES n | MES t | MES hold t | Label |
|---|---:|---:|---:|---|---:|---:|---|
| gap_on_go_only | 0 | — | — | 0 | — | 0.703 | KILL (no trades) |
| overnight_gap_fade | 43 | −0.212 | 0.007 | 30 | 1.659 | −0.691 | KILL |
| first30_fade | 41 | −0.357 | −0.236 | 23 | −1.774 | −0.173 | KILL |
| lunch_or_magnet | 44 | −1.255 | −0.146 | 43 | −0.557 | −0.726 | KILL |

Go-leg of the MES PASS family does not trade on this tape. MES overnight-gap fade is the closest this cycle (t=1.659 n=30) and still under the gate. Clock baselines unchanged: **NOT_IN_CLOCK_OR_BARS_YET**.

See `reports/cycles/cycle_16/`. Next: cycle 17 **1m** path (Databento 2024-01-01→2026-03-11) — test whether the missing MNQ edge is inside the 5m candle, not on the 5m chart.

## Cycle 17 (KILL) — 1m path inside the 5m bar

Databento MNQ 1m: discovery 598631 bars (2024-01-01→2025-09-12, **7** WF folds), holdout 172522 bars (through 2026-03-11). Not Massive 5m.

| Family | MNQ n | MNQ t | MNQ hold t | Label |
|---|---:|---:|---:|---|
| first5_break | 263 | −0.029 | 0.342 | KILL |
| overnight_gap_fade | 190 | 0.607 | 1.173 | KILL |
| first30_fade | 188 | −1.486 | −1.161 | KILL |

1m clock baselines: clock_short t=0.048, mon_fri_long t=1.177 — still **NOT_IN_CLOCK_OR_BARS_YET**. The 5-minute opening-range break (the path inside the first 5m candle) has n=263 and t≈0. Overnight-gap fade has more folds than on 5m and still t=0.607.

See `reports/cycles/cycle_17/`. Cycle 18 re-evals the closest 5m MNQ family (`vwap_reclaim_90`) and the MES lock on this 1m tape.

## Cycle 18 — PASS_MNQ `vwap_reclaim_90` on **1m**

It was the bars chart — the **1m path**, not the 5m candle. Same family on Massive 5m was WF t=1.609 n=41 (KILL). Databento MNQ 1m 2024-01-01→2026-03-11, 7 WF folds, holdout from 2025-09-12 through 2026-03-11 (tape ends March, not Massive’s Sep 2026).

Locked constructor-grid first values (and 4/7 fold winners): `min_away_atr=0.10`, `stop_atr_mult=0.20`, `entry_end_minutes=660` (11:00 ET), `first_hour_bias=True`. Sprint-1 fills. RTH entries. `max_hold_bars=36` (**36 minutes** on 1m vs 3 hours on 5m). Flatten 15:45. Overnight cling=0.

| Source | n | t | PnL |
|---|---:|---:|---:|
| Official WF 180/60 (7 folds, 6 profitable) | **282** | **3.096** | +$9363 |
| Official holdout (2025-09-12→2026-03-11) | **114** | **2.481** | **+$4129** |
| Holdout WR / PF / expectancy | 63.2% | PF 1.66 | +$36.22 / trade |
| Exits | target 51 | time_stop 36 | stop 27 |

Gate: **PASS_MNQ** (fold-search WF + locked holdout). Holdout is *positive* and t≥2 (unlike PASS_MES). Harden of the constructor lock **fails** WF t≥2 (see below). **Not** `READY_FOR_PAPER_LIVE_CANDIDATE`. MES 1m of this family not yet run. 1m `gap_on_confirm_lock` on MNQ is KILL (t=−1.26).

See `reports/cycles/cycle_18/`. Paper: `reports/paper/MNQ_1m_vwap_reclaim_90_replay.json` (matches holdout).

## Harden MNQ 1m `vwap_reclaim_90` — not paper-live

Locked grid-first combo (`min_away=0.10`, `stop=0.20`, 11:00, first-hour bias) on the **same** 1m tape:

| Check | n | t | Note |
|---|---:|---:|---|
| Locked-combo WF 180/60 | 294 | **1.847** | **fails t≥2** (fold-search WF was 3.096) |
| Locked holdout | 114 | 2.481 | unchanged |
| Diagnostic 90/30 | 428 | 2.262 | not the gate |
| Neighbor `min_away=0.08` | 329 | 3.163 | HO t=2.881 — diagnostic only |
| Neighbor `stop=0.24` | 275 | 2.97 | HO t=3.738 — diagnostic only |

Cycle 18 PASS_MNQ is fold-optimized OOS. The constructor lock does **not** independently clear WF t≥2. **Not** `READY_FOR_PAPER_LIVE_CANDIDATE`. Cycle 19 locks the other fold winner (`stop=0.30`, 3/7 folds) as a single combo.

See `reports/cycles/harden/MNQ_vwap_reclaim_90/`.

## Cycle 19 — PASS_MNQ lock `stop_atr_mult=0.30`

Single-combo lock of the other cycle-18 fold winner (3/7 folds picked 0.30). Same 1m tape. All **7/7** discovery folds profitable. Overnight=0.

| Source | n | t | PnL |
|---|---:|---:|---:|
| Official WF 180/60 (7 folds) | **259** | **3.943** | +$10094 |
| Official holdout | **87** | **3.696** | **+$4893** |
| Holdout WR / PF / expectancy | 65.5% | PF **2.66** | +$56.24 / trade |
| Max DD (holdout) | | | −$684 |
| Paper replay | 87 | — | matches holdout |

This is the official MNQ candidate (cycle-14 style lock), stronger than the grid-first 0.20 combo.

Harden (locked combo):

| Check | n | t | Note |
|---|---:|---:|---|
| Locked WF 180/60 | 259 | **3.943** | 7/7 folds; harden gate **PASS_MNQ** |
| Locked holdout | 87 | 3.696 | overnight=0 |
| Diagnostic 90/30 | 376 | **4.462** | not the gate |
| Valid ±20% neighbors | 5/5 | all t≥2.97 | `entry=528` invalid (pre-RTH), ignored |
| Cost×2 WF | 258 | **3.776** | still 7/7 |
| Cost×2 holdout | 86 | **3.964** | +$5073 |
| Holdout bootstrap | 87 | mean 3.741 | 95% CI [1.612, 5.967], 95% of draws t≥2, none <0 |

**READY_FOR_PAPER_LIVE_CANDIDATE.** Caveats: 1m holdout ends 2026-03-11 (not Massive Sep 2026); 36-minute max hold; bootstrap CI lo=1.61 <2 but >0. **No `GO_LIVE`. No live trading.**

See `reports/cycles/cycle_19/` and `reports/cycles/harden/MNQ_vwap_reclaim_90_lock/`. Paper: `reports/paper/MNQ_1m_vwap_reclaim_90_lock_replay.json`.

## Extra Massive history

Live `--plan-depth` with the cloud `MASSIVE_API_KEY`: **plan_history_2y**, earliest bar 2024-09-23. 2022–2023 tickers empty. See `reports/massive/BLOCKER.md`. Not a missing-key stop. **2024–now is the working tape.**

## Reproduce

```bash
python scripts/download_massive_futures.py --plan-depth
python scripts/research_cycle.py --cycle 15 --symbol MNQ MES
python scripts/research_cycle.py --cycle 16 --symbol MNQ MES
python scripts/research_cycle.py --cycle 17 --symbol MNQ
python scripts/research_cycle.py --cycle 18 --symbol MNQ
python scripts/harden_candidate.py --family vwap_reclaim_90 --symbol MNQ --timeframe 1m
python scripts/research_cycle.py --cycle 19 --symbol MNQ
python scripts/harden_candidate.py --family vwap_reclaim_90_lock --symbol MNQ --timeframe 1m
python scripts/run_paper_replay.py --symbol MNQ --timeframe 1m --strategy vwap_reclaim_90_lock --start 2025-09-12
python scripts/run_paper_replay.py --symbol MNQ --timeframe 1m --strategy vwap_reclaim_90 --start 2025-09-12
python scripts/harden_candidate.py --family gap_on_confirm_lock --symbol MES
python scripts/run_paper_replay.py --symbol MES --timeframe 5m --strategy gap_on_confirm --start 2025-09-12
python -m pytest tests/ -q
```
