# Massive research dumps

Paper / backtest only.

These gzip CSVs are volume-rolled front-month 5m bars pulled from Massive
Futures REST (`GET /futures/v1/aggs/{ticker}?resolution=5min`).

| File | Window (UTC) | Notes |
|---|---|---|
| `MNQ_5m.csv.gz` | 2024-09-22 → 2026-09-18 | contracts MNQH5…MNQZ6 |
| `MES_5m.csv.gz` | 2024-09-22 → 2026-09-18 | contracts MESZ4…MESU6 |

Schema: `timestamp,open,high,low,close,volume,transactions,contract` (UTC ISO).
The loader maps `timestamp` → `datetime`.

Future pulls: `Authorization: Bearer $MASSIVE_API_KEY` against
`https://api.massive.com/futures/v1/aggs/{ticker}?resolution=5min&...`
Tickers: `MNQU5`, `MESU5`, `ESU5`. Enumerate H/M/U/Z; do not rely on
`product_code` filters.

`scripts/import_massive_upload.py` rebuilds these gzips from a founder upload.
The backtest loader prefers this directory over `data/{SYM}_5m.csv`.
