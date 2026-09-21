# Massive ingest — attached dump unblocks research

Paper / backtest only. No live trading.

**Cloud `MASSIVE_API_KEY` is not required for this cycle.** Founder attached
volume-rolled 5m dumps (2024-09-22 → 2026-09-18) which are committed as
`data/massive/MNQ_5m.csv.gz` and `data/massive/MES_5m.csv.gz`.

The loader prefers those files. Future REST pulls (optional) still use:

```
Authorization: Bearer $MASSIVE_API_KEY
GET https://api.massive.com/futures/v1/aggs/{ticker}?resolution=5min&...
```

Tickers: `MNQU5`, `MESU5`, `ESU5`. Enumerate H/M/U/Z. Do not rely on
`product_code` filters.

This dump is **~2 years**, not 2020+. That is shorter than a Developer-plan
5-year pull. Research proceeds on the attached tape; a longer REST pull is
an optional later step, not a gate.
