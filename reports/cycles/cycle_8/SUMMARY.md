# Research cycle 8

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T12:17:36.350788+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `{'rows': 138366, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 13:25:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| gap_and_go | new | 10 | -2.008 | -0.189 | KILL (WF t<2 or n<30) | 10 | -6.077 | -1.63 | KILL (WF t<2 or n<30) | KILL |
| nr15_break | new | 58 | 1.044 | -0.309 | KILL (WF t<2 or n<30) | 74 | 0.359 | -2.196 | KILL (WF t<2 or n<30) | KILL |
| onh_onl_break | new | 17 | 0.447 | 0.51 | KILL (WF t<2 or n<30) | 48 | 0.028 | 0.736 | KILL (WF t<2 or n<30) | KILL |
| orb_fail_fade | new | 32 | 0.59 | 2.224 | KILL (WF t<2 or n<30) | 38 | -0.013 | -0.007 | KILL (WF t<2 or n<30) | KILL |
| s2_mes_sens_7 | hunt | 4 | 0.008 | 0.558 | KILL (WF t<2 or n<30) | 39 | 0.414 | -0.073 | KILL (WF t<2 or n<30) | KILL |
| spread_fade | near_miss | 52 | 0.997 | 0.909 | KILL (WF t<2 or n<30) | 46 | -1.182 | -0.863 | KILL (WF t<2 or n<30) | KILL |
| volume_dryup_break | new | 50 | -1.447 | -0.327 | KILL (WF t<2 or n<30) | 69 | -0.362 | -0.586 | KILL (WF t<2 or n<30) | KILL |
| wick_reject_cont | new | 44 | -0.497 | 0.823 | KILL (WF t<2 or n<30) | 44 | -0.458 | 1.099 | KILL (WF t<2 or n<30) | KILL |

Labels: **PASS_MNQ** / **PASS_MNQ_PROVISIONAL** (thin holdout n<30), **PASS_MES** / **PASS_MES_PROVISIONAL**, **PASS_BOTH**, **KILL**. Paper only. No live trading. READY_FOR_PAPER_LIVE_CANDIDATE only after harden.

