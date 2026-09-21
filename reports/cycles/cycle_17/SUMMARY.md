# Research cycle 17

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T14:02:57.821756+00:00`

## Tape

- MNQ: `{'rows': 771153, 'start': '2024-01-01 23:00:00+00:00', 'end': '2026-03-11 23:59:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `None`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| first30_fade | new | 188 | -1.486 | -1.161 | KILL (WF t<2 or n<30) | None | None | None |  | KILL |
| first5_break | new | 263 | -0.029 | 0.342 | KILL (WF t<2 or n<30) | None | None | None |  | KILL |
| overnight_gap_fade | new | 190 | 0.607 | 1.173 | KILL (WF t<2 or n<30) | None | None | None |  | KILL |

Labels: **PASS_MNQ** / **PASS_MNQ_PROVISIONAL** (thin holdout n<30), **PASS_MES** / **PASS_MES_PROVISIONAL**, **PASS_BOTH**, **KILL**. Paper only. No live trading. READY_FOR_PAPER_LIVE_CANDIDATE only after harden.

