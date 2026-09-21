# Research cycle 7

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T12:18:20.878787+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `None`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| orb_retrace_3_dense | hunt | 29 | -0.205 | -0.913 | KILL (WF t<2 or n<30) | None | None | None |  | KILL |
| vwap_reclaim_90_adx | hunt | 37 | 0.656 | 2.116 | KILL (WF t<2 or n<30) | None | None | None |  | KILL |
| vwap_reclaim_90_dense | hunt | 45 | 1.357 | 1.391 | KILL (WF t<2 or n<30) | None | None | None |  | KILL |
| vwap_reclaim_90_vol | hunt | 41 | 1.609 | 2.116 | KILL (WF t<2 or n<30) | None | None | None |  | KILL |

Labels: **PASS_MNQ** / **PASS_MNQ_PROVISIONAL** (thin holdout n<30), **PASS_MES** / **PASS_MES_PROVISIONAL**, **PASS_BOTH**, **KILL**. Paper only. No live trading. READY_FOR_PAPER_LIVE_CANDIDATE only after harden.

