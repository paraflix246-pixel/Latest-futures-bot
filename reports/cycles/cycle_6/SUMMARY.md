# Research cycle 6

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T05:58:30.613338+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `{'rows': 138366, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 13:25:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| filtered_orb_2 | hunt | 8 | -0.157 | 0.425 | KILL (WF t<2 or n<30) | 42 | 0.366 | -0.854 | KILL (WF t<2 or n<30) | KILL |
| filtered_orb_5m | hunt | 1 | None | 1.497 | KILL (WF t<2 or n<30) | 40 | -0.259 | -0.361 | KILL (WF t<2 or n<30) | KILL |
| filtered_orb_90 | hunt | 6 | -0.278 | 0.232 | KILL (WF t<2 or n<30) | 37 | 0.122 | -1.449 | KILL (WF t<2 or n<30) | KILL |
| filtered_orb_adx | hunt | 7 | -0.411 | 0.282 | KILL (WF t<2 or n<30) | 30 | 0.526 | -0.165 | KILL (WF t<2 or n<30) | KILL |
| orb_retrace_3 | hunt | 32 | 1.247 | -0.784 | KILL (WF t<2 or n<30) | 39 | 0.403 | -1.052 | KILL (WF t<2 or n<30) | KILL |
| orb_retrace_x | hunt | 48 | -0.076 | -0.521 | KILL (WF t<2 or n<30) | 55 | -1.038 | -0.938 | KILL (WF t<2 or n<30) | KILL |
| vwap_reclaim | hunt | 44 | 0.948 | 1.352 | KILL (WF t<2 or n<30) | 14 | -0.261 | -1.43 | KILL (WF t<2 or n<30) | KILL |
| vwap_reclaim_90 | hunt | 41 | 1.609 | 2.116 | KILL (WF t<2 or n<30) | 28 | 0.572 | 0.1 | KILL (WF t<2 or n<30) | KILL |

Labels: **PASS_MNQ** (MNQ-only candidate, trade-MNQ-only is allowed), **PASS_MES**, **PASS_BOTH**, **KILL**. Paper only. No live trading.
