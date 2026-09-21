# Status — Massive attached tape (2024-09 → 2026-09)

Paper/backtest only. **Not live trading. No profit guarantee.**

PR: https://github.com/paraflix246-pixel/Latest-futures-bot/pull/3  
Branch: `cursor/massive-long-tape-research-6b77`

## Bottom line

Founder attached Massive 5m dumps. Research is **not blocked** on a cloud `MASSIVE_API_KEY`.

| Tape | Rows | UTC window | Source |
|---|---:|---|---|
| MNQ 5m | 137,304 | 2024-09-22 → 2026-09-18 | `data/massive/MNQ_5m.csv.gz` (volume-rolled) |
| MES 5m | 138,366 | 2024-09-22 → 2026-09-18 | `data/massive/MES_5m.csv.gz` |

This is ~2 years, ending six months later than the old Databento tape (which stopped 2026-03-11). It is **not** 2020+. Loader prefers these gzips.

Kill-gate cycle is running / will be filled below. Live trading stays off.

## Kill gate (unchanged)

- MNQ walk-forward OOS t-stat ≥ 2.0 on ≥ 30 trades
- MES replication not a clear loss (t ≥ 0 preferred)
- Sprint-1 realistic fills (`next_open`, exit slip, gap-aware)
- RTH flatten / no overnight clinging

## Massive auth (future pulls only)

```
Authorization: Bearer $MASSIVE_API_KEY
GET https://api.massive.com/futures/v1/aggs/{ticker}?resolution=5min&...
```

Tickers that work: `MNQU5`, `MESU5`, `ESU5`. Enumerate H/M/U/Z. `product_code` filters are flaky.

## Cycle 1 (in progress)

Families: ensemble, orb_crabel, last30_momentum, vol_squeeze_expansion, impulse_clock, vol_gated_ensemble, ib_extension, on_inventory, lunch_range_break.

Engine: sprint-1 after. Holdout locked at `2025-09-12`.

_Metrics table will be written by `scripts/research_cycle.py --cycle 1`._

## Reproduce

```bash
python scripts/research_cycle.py --cycle 1
python -m pytest tests/ -q
```
