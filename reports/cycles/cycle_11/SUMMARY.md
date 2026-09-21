# Research cycle 11

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T12:34:45.811525+00:00`

## Tape

- MNQ: `{'rows': 46783, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:45:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `None`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| keltner_am_fade | new | 0 | None | None | KILL (WF t<2 or n<30) | None | None | None |  | KILL |
| morning_range_break | new | 0 | None | None | KILL (WF t<2 or n<30) | None | None | None |  | KILL |
| pivot_bounce | new | 0 | None | None | KILL (WF t<2 or n<30) | None | None | None |  | KILL |
| vwap_reclaim_90_target | hunt | 0 | None | None | KILL (WF t<2 or n<30) | None | None | None |  | KILL |

Labels: **PASS_MNQ** / **PASS_MNQ_PROVISIONAL** (thin holdout n<30), **PASS_MES** / **PASS_MES_PROVISIONAL**, **PASS_BOTH**, **KILL**. Paper only. No live trading. READY_FOR_PAPER_LIVE_CANDIDATE only after harden.

