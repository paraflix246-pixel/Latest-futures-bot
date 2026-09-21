# bott-trader — MNQ / NQ / MES Futures Backtester

A clean, from-scratch backtester for micro/mini index futures (MNQ, NQ, MES),
built around three independent strategy edges plus a regime-switch ensemble.
Old strategy/backtest code from the previous iteration of this project has
been archived under `legacy/` (not deleted) rather than deleted outright.

**Paper / backtest only.** These simulations do not imply live profitability
and are not a profit guarantee. Do not enable live trading without an
explicit later go-ahead.

## Quick start

```bash
pip install -r requirements.txt
python scripts/run_backtest.py --symbol MNQ --timeframe 5m --strategy ensemble \
    --start 2025-12-29 --end 2026-03-11
```

Results (trade log, equity curve, summary metrics) are written to `reports/`.

Sprint improve-loop (walk-forward + locked holdout, before/after):

```bash
python scripts/run_sprint.py --phase after
python scripts/run_sprint.py --phase compare
```

See `reports/sprint1/` for cost assumptions, diagnosis, and IS vs OOS tables.

## Strategies

| Name | Edge |
|---|---|
| `trend` | EMA(20/50) crossover confirmed by EMA(200), ATR trailing stop |
| `mean_reversion` | Bollinger(20,2σ) + RSI(14) fade, gated by ADX < 20 |
| `breakout` | Donchian(20) channel break with volume confirmation |
| `ensemble` | ADX regime router: trend when ADX≥25, mean-reversion when ADX<20, breakout evaluated independently and given priority |
| `vwap_cross` | EMA(10/20) cross + session VWAP filter + 3-candle confirmation delay before entering |
| `orb_break_fade` | RTH opening-range break; fade a failed break with a tight stop; flatten at cash close |
| `orb_crabel` | Filtered ORB (VWAP + RVOL + OR-width/ATR) with 11:00 ET clock; fade failed breaks |
| `vol_squeeze_expansion` | Bollinger-inside-Keltner width-percentile squeeze, then volume break; time stop + RTH flatten |
| `impulse_clock` | Short-horizon continuation after a large-range RTH bar; max bars in trade; flatten EOD |
| `last30_momentum` | First-30m RTH return → last-30m continuation; flatten at cash close |

Walk-forward of the five RTH modules: **no validated edge** (see `reports/new_strategies/`). Paper / backtest only.

Run any strategy against any symbol/timeframe via `scripts/run_backtest.py
--strategy {trend,mean_reversion,breakout,ensemble}`.

## Data

`data/MNQ_1m.csv`, `MNQ_5m.csv`, `MES_1m.csv`, `MES_5m.csv` — real OHLCV,
2024-01-01 to 2026-03-11 (MNQ 5m is the sprint-1 baseline tape). **NQ has no standalone feed**: since NQ and MNQ
track the same index at the same price (same tick size), NQ backtests reuse
MNQ's price series with NQ's own contract multiplier/margin/commission
applied (see `config/settings.py: DERIVED_SYMBOLS`). NQ's much larger
multiplier means it needs a bigger account/risk budget to size any contracts
at all — expect low or zero trade counts on a small account.

Default fills: next-bar open ± 1 tick, exit slippage, gap-aware stops.
Round-trip MNQ friction is documented in `reports/sprint1/COST_ASSUMPTIONS.md`
(~$0.62 commission + 2 ticks slippage ≈ $1.62/contract). Legacy signal-close
fills remain available on `run_backtest` via engine kwargs for reproduction.

## Structure

```
config/
  instruments.py   # contract specs (MNQ/NQ/MES) via src/instruments registry
  settings.py       # account size, risk %, default timeframe, symbols
src/
  data/loader.py    # CSV loading + NQ-from-MNQ derivation
  strategies/       # trend_following, mean_reversion, breakout, ensemble
  backtest/         # engine.py (bar-by-bar sim), metrics.py
  risk/             # fixed-fractional position sizing
scripts/run_backtest.py
tests/              # pytest — engine + strategy signal sanity checks
reports/            # per-run trade log, equity curve, summary.json
legacy/             # archived prior implementation (forex bot, live trading
                     # scripts, old backtest engine) — not deleted, just parked
```

## Tests

```bash
python -m pytest tests/ -v
```
