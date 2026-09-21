# Research cycle 13

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T12:50:58.904648+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `{'rows': 138366, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 13:25:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| am_measured | new | 36 | 0.382 | -1.193 | KILL (WF t<2 or n<30) | 38 | -1.095 | -0.494 | KILL (WF t<2 or n<30) | KILL |
| gap_on_confirm | new | 28 | -1.507 | -1.002 | KILL (WF t<2 or n<30) | 36 | 3.656 | -1.594 | KILL (holdout strongly negative t=-1.594) | KILL |
| open_reject | new | 30 | -0.602 | -1.799 | KILL (WF t<2 or n<30) | 39 | -3.168 | -3.84 | KILL (WF t<2 or n<30) | KILL |
| vwap_hold_late | new | 49 | -0.501 | -0.5 | KILL (WF t<2 or n<30) | 67 | 0.216 | -1.287 | KILL (WF t<2 or n<30) | KILL |

Labels: **PASS_MNQ** / **PASS_MNQ_PROVISIONAL** (thin holdout n<30), **PASS_MES** / **PASS_MES_PROVISIONAL**, **PASS_BOTH**, **KILL**. Paper only. No live trading. READY_FOR_PAPER_LIVE_CANDIDATE only after harden.

