# Massive ingest blocker

Paper / backtest only. No live trading.

**Kind:** `missing_api_key`

**Detail:** `MASSIVE_API_KEY` is not set in this Cloud Agent environment. The client and `scripts/download_massive_futures.py` are implemented and will read the env var (never print it). Auth styles tried in order: `Authorization: Bearer`, `?apiKey=`, both, `X-API-KEY`.

Founder action: set `MASSIVE_API_KEY` in the Cloud Agent / machine environment (never commit it). Futures history depth depends on the Massive plan (Basic/Starter ≈ 2y, Developer ≈ 5y, Advanced = full history back to 2017-04-03).

Until the key is present, research cycles run on the existing Databento 2024-01 → 2026-03 MNQ/MES 5m tape. That is **not** the requested 2020+ long tape.
