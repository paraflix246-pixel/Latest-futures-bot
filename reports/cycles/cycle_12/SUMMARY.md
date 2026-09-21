# Research cycle 12

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T12:46:27.768666+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `{'rows': 138366, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 13:25:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| gap_on_range | new | 46 | 0.15 | -1.405 | KILL (WF t<2 or n<30) | 45 | 1.213 | -0.285 | KILL (WF t<2 or n<30) | KILL |
| rvol_dir_open15 | new | 14 | -2.282 | -1.216 | KILL (WF t<2 or n<30) | 19 | -0.274 | 0.581 | KILL (WF t<2 or n<30) | KILL |
| trend15_pb5_chop | new | 41 | 0.101 | -1.328 | KILL (WF t<2 or n<30) | 68 | -1.374 | 0.662 | KILL (WF t<2 or n<30) | KILL |
| vwap_fh_reclaim | new | 38 | -1.288 | -1.417 | KILL (WF t<2 or n<30) | 62 | -0.373 | -1.933 | KILL (WF t<2 or n<30) | KILL |

Labels: **PASS_MNQ** / **PASS_MNQ_PROVISIONAL** (thin holdout n<30), **PASS_MES** / **PASS_MES_PROVISIONAL**, **PASS_BOTH**, **KILL**. Paper only. No live trading. READY_FOR_PAPER_LIVE_CANDIDATE only after harden.

