# Research cycle 15

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T13:46:09.124604+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `{'rows': 138366, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 13:25:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| cross_lead_open15 | new | 43 | -1.515 | -1.075 | KILL (WF t<2 or n<30) | 44 | -0.513 | -1.518 | KILL (WF t<2 or n<30) | KILL |
| gap_on_fill_only | new | 25 | -1.157 | -0.904 | KILL (WF t<2 or n<30) | 25 | 2.679 | -0.724 | KILL (WF t<2 or n<30) | KILL |
| vol_clock_fade | new | 2 | 0.258 | -0.397 | KILL (WF t<2 or n<30) | 34 | -0.91 | -1.601 | KILL (WF t<2 or n<30) | KILL |
| weekday_gap_clock | new | 19 | -1.219 | -0.264 | KILL (WF t<2 or n<30) | 29 | -1.021 | -0.907 | KILL (WF t<2 or n<30) | KILL |

Labels: **PASS_MNQ** / **PASS_MNQ_PROVISIONAL** (thin holdout n<30), **PASS_MES** / **PASS_MES_PROVISIONAL**, **PASS_BOTH**, **KILL**. Paper only. No live trading. READY_FOR_PAPER_LIVE_CANDIDATE only after harden.

