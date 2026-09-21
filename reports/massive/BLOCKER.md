# Massive extra-history blocker

Paper / backtest only. No live trading.

**Kind:** `plan_depth_or_rate_limit`

Auth succeeded (`Authorization: Bearer`, HTTP 200). A 2020-01-01 5m pull was
attempted for MNQ and MES. Outcomes:

- Many HMUZ contract requests returned **HTTP 429** after retries.
- Contracts that did return bars start around **2024-09**, matching the
  already-committed gzip dumps. No usable pre-2024 overlap.
- `pick_front_month` then raised `No overlapping contracts to roll` because
  too many names were skipped.

The attached tape (`data/massive/*.csv.gz`, 2024-09-22 → 2026-09-18) remains
the research tape. Discovery before the locked holdout `2025-09-12` still
supports only **two** 180/60 walk-forward folds.

Founder: a longer-history Massive futures plan (Developer/Advanced) plus a
higher rate limit would thicken OOS samples. Do not fabricate bars.
