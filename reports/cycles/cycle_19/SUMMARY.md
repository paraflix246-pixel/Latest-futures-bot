# Research cycle 19

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T14:39:18.262733+00:00`

## Tape

- MNQ: `{'rows': 771153, 'start': '2024-01-01 23:00:00+00:00', 'end': '2026-03-11 23:59:00+00:00', 'source': 'load_ohlcv (Massive gzip preferred for 5m; Databento CSV for 1m) [1m]'}`
- MES: `None`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| vwap_reclaim_90_lock | hunt | 259 | 3.943 | 3.696 | PASS_MNQ | None | None | None |  | PASS_MNQ |

Labels: **PASS_MNQ** / **PASS_MNQ_PROVISIONAL** (thin holdout n<30), **PASS_MES** / **PASS_MES_PROVISIONAL**, **PASS_BOTH**, **KILL**. Paper only. No live trading. READY_FOR_PAPER_LIVE_CANDIDATE only after harden.

