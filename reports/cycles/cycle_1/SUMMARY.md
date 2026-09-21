# Research cycle 1

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T05:26:49.723626+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `{'rows': 138366, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 13:25:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- Holdout start (locked): `2025-09-12`
- WF: 180d train / 60d test

## Metrics

| Family | Kind | MNQ n | MNQ PnL | MNQ t | MES n | MES PnL | MES t | Holdout MNQ t | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|
| ensemble | prior | 72 | -1238.21 | -0.955 | 104 | -2038.93 | -1.762 | 1.3 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |
| ib_extension | new | 16 | -1044.14 | -1.352 | 48 | -557.57 | -0.363 | 0.103 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |
| impulse_clock | prior | 74 | -711.68 | -0.353 | 71 | -3123.89 | -1.547 | 1.479 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |
| last30_momentum | prior | 42 | -717.47 | -0.899 | 16 | -285.33 | -0.537 | -1.414 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |
| lunch_range_break | new | 7 | -48.96 | -0.129 | 24 | -324.16 | -0.512 | 1.303 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |
| on_inventory | new | 23 | 843.27 | 1.007 | 28 | -425.24 | -0.723 | -0.094 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |
| orb_crabel | prior | 20 | -1003.3 | -1.076 | 30 | -1613.16 | -1.37 | 0.804 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |
| vol_gated_ensemble | new | 9 | -53.17 | -0.165 | 35 | 371.38 | 0.496 | 1.536 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |
| vol_squeeze_expansion | prior | 14 | -1417.61 | -2.437 | 14 | -306.76 | -0.396 | 0.143 | KILLED (MNQ walk-forward OOS t<2 or under-traded) |

No live orders. Survivors still need GO_LIVE_CHECKLIST + founder OK.
