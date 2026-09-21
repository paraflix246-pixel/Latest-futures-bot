# Research cycle 16

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T13:50:09.805821+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `{'rows': 138366, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 13:25:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| first30_fade | new | 41 | -0.357 | -0.236 | KILL (WF t<2 or n<30) | 23 | -1.774 | -0.173 | KILL (WF t<2 or n<30) | KILL |
| gap_on_go_only | new | 0 | None | None | KILL (WF t<2 or n<30) | 0 | None | 0.703 | KILL (WF t<2 or n<30) | KILL |
| lunch_or_magnet | new | 44 | -1.255 | -0.146 | KILL (WF t<2 or n<30) | 43 | -0.557 | -0.726 | KILL (WF t<2 or n<30) | KILL |
| overnight_gap_fade | new | 43 | -0.212 | 0.007 | KILL (WF t<2 or n<30) | 30 | 1.659 | -0.691 | KILL (WF t<2 or n<30) | KILL |

Labels: **PASS_MNQ** / **PASS_MNQ_PROVISIONAL** (thin holdout n<30), **PASS_MES** / **PASS_MES_PROVISIONAL**, **PASS_BOTH**, **KILL**. Paper only. No live trading. READY_FOR_PAPER_LIVE_CANDIDATE only after harden.

