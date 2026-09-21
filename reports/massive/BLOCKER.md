# Massive extra-history blocker

Paper / backtest only. No live trading.

**Kind:** `plan_history_2y`

`MASSIVE_API_KEY` **is set** in this Cloud Agent environment. The client reads
it from `os.environ` only and never prints it. Auth: Bearer HTTP 200.

A live `--plan-depth` probe (1session bars, 2017-01-01 → today) on 2022–2025
HMUZ names:

| Ticker | n | first session | last session |
|---|---:|---|---|
| MNQZ4 | 64 | 2024-09-23 | 2024-12-20 |
| MNQU5 | 219 | 2024-10-01 | 2025-09-19 |
| MESU5 | 214 | 2024-09-24 | 2025-09-19 |
| MNQH4 / MNQZ3 / MNQH3 / MNQZ2 / MNQH2 / MESZ3 / MESH3 | 0 | — | — |

Earliest nonempty bar: **2024-09-23**. That is exactly Massive **Futures Basic/Starter = 2 years** (from 2026-09-21 → ~2024-09-21) and matches the attached gzip dumps (`2024-09-22` → `2026-09-18`).

This is **not** `BLOCKED_NEED_MASSIVE_ENV`. The key works. Pre-2024 bars are empty because the **plan history window is 2 years**, not because the client is missing. Do not fabricate bars.

Front-month roll now infers HMUZ last-trade dates when `/contracts` omits expiry, so a future Developer/Advanced pull can stitch. 429 handling honors `Retry-After`.

Founder: upgrade Massive futures to **Developer (5y)** or **Advanced (2017-04-03)** to thicken OOS (more than two 180/60 folds). Research continues on the 2-year tape.

See `reports/massive/PLAN_DEPTH.md`.
