# Research cycle 2

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T05:31:35.742487+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `{'rows': 138366, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 13:25:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ PnL | MNQ t | MES n | MES PnL | MES t | Holdout MNQ t | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| afternoon_momentum | new | 25 | -445.3 | -0.521 | 33 | -834.3 | -1.052 | -0.145 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |
| am_vwap_reclaim | new | 48 | -1733.27 | -1.49 | 61 | 559.79 | 0.437 | -1.882 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |
| failed_ib_fade | new | 61 | -4115.72 | -2.264 | 58 | 2713.98 | 0.853 | -0.908 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |
| open_drive | new | 28 | -596.65 | -0.681 | 35 | -1691.41 | -1.71 | 0.107 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |

No live orders. Survivors still need GO_LIVE_CHECKLIST + founder OK.
