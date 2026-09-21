# Research cycle 9

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T12:25:03.400558+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `{'rows': 138366, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 13:25:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| higher_low_vwap | new | 33 | -1.035 | 0.386 | KILL (WF t<2 or n<30) | 25 | 1.394 | -1.574 | KILL (WF t<2 or n<30) | KILL |
| ib_hold_break | new | 37 | -0.936 | 0.903 | KILL (WF t<2 or n<30) | 66 | 0.094 | 0.364 | KILL (WF t<2 or n<30) | KILL |
| inside_hour_break | new | 2 | 0.08 | 0.261 | KILL (WF t<2 or n<30) | 35 | -1.217 | -0.654 | KILL (WF t<2 or n<30) | KILL |
| prior_mid_reclaim | new | 13 | -0.633 | -0.551 | KILL (WF t<2 or n<30) | 18 | 0.447 | -0.173 | KILL (WF t<2 or n<30) | KILL |

Labels: **PASS_MNQ** / **PASS_MNQ_PROVISIONAL** (thin holdout n<30), **PASS_MES** / **PASS_MES_PROVISIONAL**, **PASS_BOTH**, **KILL**. Paper only. No live trading. READY_FOR_PAPER_LIVE_CANDIDATE only after harden.

