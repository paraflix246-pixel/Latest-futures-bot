# Research cycle 4

Paper / backtest only. Sprint-1 realistic fills. No live trading.

Generated: `2026-09-21T05:44:19.535516+00:00`

## Tape

- MNQ: `{'rows': 137304, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 20:55:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- MES: `{'rows': 138366, 'start': '2024-09-22 22:00:00+00:00', 'end': '2026-09-18 13:25:00+00:00', 'source': 'data/{SYM}_5m.csv (Massive if promoted, else existing Databento 2024+ tape)'}`
- Holdout start (locked): `2025-09-12`
- WF: see run log (default 180d/60d)

## Metrics

| Family | Kind | MNQ n | MNQ t | MNQ hold t | MNQ | MES n | MES t | MES hold t | MES | Label |
|---|---|---:|---:|---:|---|---:|---:|---:|---|---|
| adr_exhaust_fade | new | 15 | 0.908 | 0.144 | KILL (WF t<2 or n<30) | 16 | -0.632 | 0.233 | KILL (WF t<2 or n<30) | KILL |
| gap_fill_go | new | 25 | 0.02 | 1.147 | KILL (WF t<2 or n<30) | 24 | 0.743 | -0.846 | KILL (WF t<2 or n<30) | KILL |
| morning_reversal | new | 21 | -1.034 | 0.3 | KILL (WF t<2 or n<30) | 44 | 0.152 | 0.449 | KILL (WF t<2 or n<30) | KILL |
| pdh_pdl_fail | new | 41 | 0.956 | -0.828 | KILL (WF t<2 or n<30) | 45 | 0.829 | -1.115 | KILL (WF t<2 or n<30) | KILL |
| rvol_open15 | new | 1 | None | -0.505 | KILL (WF t<2 or n<30) | 16 | 0.12 | -1.416 | KILL (WF t<2 or n<30) | KILL |
| vwap_band_fade | new | 35 | -0.219 | -1.249 | KILL (WF t<2 or n<30) | 12 | -2.052 | -0.676 | KILL (WF t<2 or n<30) | KILL |

Labels: **PASS_MNQ** (MNQ-only candidate, trade-MNQ-only is allowed), **PASS_MES**, **PASS_BOTH**, **KILL**. Paper only. No live trading.
