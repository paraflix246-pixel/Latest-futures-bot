# Research cycle 3

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T05:40:03.858613+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `{'rows': 138366, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 13:25:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| orb_filtered_15 | new | 74 | 0.804 | -0.303 | KILL (WF t<2 or n<30) | 77 | -0.585 | -1.181 | KILL (WF t<2 or n<30) | KILL |
| orb_filtered_30 | new | 69 | -0.583 | 0.521 | KILL (WF t<2 or n<30) | 77 | -0.398 | 0.773 | KILL (WF t<2 or n<30) | KILL |
| orb_filtered_5 | new | 75 | -1.268 | -0.422 | KILL (WF t<2 or n<30) | 79 | -0.529 | -1.643 | KILL (WF t<2 or n<30) | KILL |
| orb_filtered_retest | new | 54 | 0.157 | 0.607 | KILL (WF t<2 or n<30) | 55 | 0.108 | -0.523 | KILL (WF t<2 or n<30) | KILL |
| orb_retrace | new | 41 | 0.392 | -0.757 | KILL (WF t<2 or n<30) | 58 | 0.446 | -1.234 | KILL (WF t<2 or n<30) | KILL |
| trend15_pullback5 | new | 47 | 0.719 | 0.525 | KILL (WF t<2 or n<30) | 51 | 0.321 | 0.519 | KILL (WF t<2 or n<30) | KILL |
| vwap_hour_reclaim_fail | new | 42 | -0.232 | -0.15 | KILL (WF t<2 or n<30) | 51 | -0.176 | 0.722 | KILL (WF t<2 or n<30) | KILL |

Labels: **PASS_MNQ** (MNQ-only candidate, trade-MNQ-only is allowed), **PASS_MES**, **PASS_BOTH**, **KILL**. Paper only. No live trading.
