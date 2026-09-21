# Research cycle 10

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T12:32:31.648998+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `{'rows': 138366, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 13:25:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| inside_day_orb | new | 2 | -4.652 | 0.894 | KILL (WF t<2 or n<30) | 3 | -0.561 | -0.579 | KILL (WF t<2 or n<30) | KILL |
| keltner_am_fade | new | 45 | 1.122 | -0.206 | KILL (WF t<2 or n<30) | 70 | -2.963 | -1.045 | KILL (WF t<2 or n<30) | KILL |
| morning_range_break | new | 17 | -0.123 | 0.9 | KILL (WF t<2 or n<30) | 54 | -0.057 | 0.391 | KILL (WF t<2 or n<30) | KILL |
| pivot_bounce | new | 32 | 0.311 | -0.817 | KILL (WF t<2 or n<30) | 39 | 1.339 | -0.898 | KILL (WF t<2 or n<30) | KILL |
| vwap_reclaim_90_target | hunt | 41 | 1.546 | 1.572 | KILL (WF t<2 or n<30) | 27 | 0.902 | -0.49 | KILL (WF t<2 or n<30) | KILL |

Labels: **PASS_MNQ** / **PASS_MNQ_PROVISIONAL** (thin holdout n<30), **PASS_MES** / **PASS_MES_PROVISIONAL**, **PASS_BOTH**, **KILL**. Paper only. No live trading. READY_FOR_PAPER_LIVE_CANDIDATE only after harden.

