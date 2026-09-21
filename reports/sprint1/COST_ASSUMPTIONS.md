# Cost and fill assumptions (sprint 1)

Paper/backtest only. These are modeled costs, not a live brokerage statement.
Nothing here is a profit guarantee.

## Account / risk

| Item | Value | Notes |
|---|---|---|
| Starting equity | $50,000 | `config/settings.py` `DEFAULT_ACCOUNT_SIZE` |
| Risk per trade | 0.5% of equity | fixed-fractional vs stop distance |
| Max contracts | 10 (after) / uncapped (before) | tight stops cannot explode size |
| Daily loss halt | 2% of day-start equity (after) | new entries halt; open trade still managed |
| Cooldown | 3 bars / 15 minutes after an exit (after) | plus no same-bar re-entry |
| Flatten | last RTH bar 16:00 ET (after, ensemble overlay) | no overnight hold from the sprint overlay |

## Instrument (MNQ)

| Item | Value | Source |
|---|---|---|
| Tick size | 0.25 | CME MNQ |
| Tick value | $0.50 | $2/point × 0.25 |
| Round-trip commission | $0.62 / contract | `InstrumentSpec.commission_rt` (typical micro) |
| Quoted spread default | 0.50 (2 ticks) | registry `spread_default`; **not** auto-applied as extra spread on top of slippage |

## Fill model

**Before (legacy, reproduced as `fill_model="signal_close"`):**

- Enter at signal-bar **close** + 1 tick slippage
- Exit at exact stop/target/trail with **zero** exit slippage
- Trailing stop can tighten on the same bar that is then used for the stop check (OHLC ambiguity, optimistic)
- Same-bar re-entry after an exit was allowed (365 of 3,325 full-sample ensemble trades)

**After (default `fill_model="next_open"`):**

- Signal at bar close, fill at **next open** ± 1 tick
- Exit slippage: 1 tick on stop, target, trail, flatten, and EOD
- Gap through a stop fills at the **gapped open**, not the stop (worse)
- Gap through a target fills at the **target**, not a better open (no free gap profit)
- Trail/breakeven updates apply from the **next** bar
- No same-bar re-entry; optional cooldown

Round-trip friction per MNQ contract after the fix, typical (no gap):

- Commission $0.62
- Slippage 2 ticks × $0.50 = $1.00
- **All-in ≈ $1.62 / contract RT**

Stress case matching `spread_default` (2 ticks each way) would be $2.00 slippage + $0.62 = $2.62 RT. The sprint uses the 1-tick-per-fill base case and reports modeled slippage as its own column.

## Data

- `data/MNQ_5m.csv`, 2024-01-01 23:00 UTC → 2026-03-11 23:55 UTC, 154,263 bars
- In-sample / discovery: bars **before** 2025-09-12
- Locked holdout OOS: 2025-09-12 → 2026-03-11 (not used to choose the engineering fixes)
- Walk-forward: 180-day train / 60-day test, rolling by 60 days, concatenated OOS only

The engineering changes (event-trigger, fill realism, same-bar re-entry, contract cap, RTH overlay) were chosen from the **before** diagnosis, not from scanning the holdout.
