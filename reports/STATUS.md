# Status — Massive long-tape research

Paper/backtest only. **Not live trading. No profit guarantee. No validated edge yet.**

Branch: `cursor/massive-long-tape-research-6b77`  
Credit-light: one PR stream. PR #2 (RTH session strategies) is useful for modules, but its engine was a signal-close regression — **this stream keeps sprint-1 next-open fills**.

## Bottom line (this turn)

1. **Massive client + ingest scripts are implemented.** Auth tries Bearer, then `apiKey` query, then both, then `X-API-KEY`. The key is read from `MASSIVE_API_KEY` and never printed.
2. **`MASSIVE_API_KEY` is not set in this Cloud Agent environment.** Ingest cannot run until the founder adds the key. That is a written blocker, not a silent skip.
3. Prior candidates from PR #2 (filtered ORB / last30 / squeeze / impulse) plus the sprint-1 ensemble are wired for re-eval on whatever tape we have, using the **realistic sprint-1 engine**.
4. New families (not EMA/ADX/Donchian retunes): `ib_extension`, `on_inventory`, `lunch_range_break`, `vol_gated_ensemble`.
5. Live trading is still disabled. No `GO_LIVE_CHECKLIST.md` until a kill-gate survivor exists.

## Kill gate

| Rule | Bar |
|---|---|
| MNQ walk-forward OOS t-stat | ≥ 2.0 on ≥ 30 trades |
| MES (or ES) replication | not a clear loss (t ≥ 0 preferred) |
| Fills | sprint-1 engine (`next_open`, exit slip, gap-aware stops) |
| Session | RTH-capable; flatten at cash close; no overnight clinging |

## Massive

| Item | State |
|---|---|
| Client | `src/data/massive_client.py` |
| Ingest | `scripts/download_massive_futures.py` |
| Roll | volume-priority front month + backward ratio adjust |
| Env | `MASSIVE_API_KEY` **missing in this pod** |
| Founder action | set the key in Cloud Agent / machine env, then re-run ingest |

Plan history if/when the key works: Basic/Starter ≈ 2y, Developer ≈ 5y (2020+), Advanced = 2017-04-03+.

Existing local tape (until Massive promotes a longer file): MNQ/MES 5m **2024-01-01 → 2026-03-11**.

## Families in the cycle

| Family | Kind | Note |
|---|---|---|
| ensemble | prior | Sprint-1 after (RTH, event trigger, no range breakout override) |
| orb_crabel | prior | VWAP + RVOL + OR-width filter; 11:00 clock |
| last30_momentum | prior | First-30m → last-30m continuation |
| vol_squeeze_expansion | prior | BB-inside-Keltner squeeze release |
| impulse_clock | prior | MNQ false positive on short tape / MES fail (PR #2) |
| vol_gated_ensemble | new | Same ensemble, silent in extreme ATR percentiles |
| ib_extension | new | 60-minute initial balance, not 15m ORB |
| on_inventory | new | Overnight continuation via VWAP pullback (not gap fade) |
| lunch_range_break | new | 11:30–13:30 compression break |

## Cycle table

_Cycle 1 numbers will be filled after the first `research_cycle.py` run on the available tape._

## Dead ends we will not re-open

- EMA / ADX / Donchian length fishing
- PR #2 signal-close engine (less realistic than sprint-1)
- Overnight gap *reversion* (already null)
- Calling holdout PnL an edge when WF t < 2

## Reproduce

```bash
python scripts/download_massive_futures.py --probe
python scripts/download_massive_futures.py --start 2020-01-01 --resolutions 5min --promote
python scripts/research_cycle.py --cycle 1
python -m pytest tests/ -q
```
