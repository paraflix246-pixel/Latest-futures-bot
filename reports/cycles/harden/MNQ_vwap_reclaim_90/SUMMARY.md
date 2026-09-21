# Harden MNQ `vwap_reclaim_90`

Paper / backtest only. Sprint-1 fills. No live trading.

Locked params: `{'min_away_atr': 0.1, 'stop_atr_mult': 0.2, 'entry_end_minutes': 660, 'first_hour_bias': True}`

- Official WF 180/60: n=294 t=1.847 pnl=6058.65
- Holdout from 2025-09-12: n=114 t=2.481 pnl=4129.19 overnight=0
- Gate: **KILL (WF t<2 or n<30)**
- Diagnostic WF 90/30 (not the gate): n=428 t=2.262

## Sensitivity (±20% one-factor)

| Variant | WF n | WF t | HO n | HO t | Gate |
|---|---:|---:|---:|---:|---|
| locked | 294 | 1.847 | 114 | 2.481 | KILL (WF t<2 or n<30) |
| min_away_atr=0.08 | 329 | 3.163 | 124 | 2.881 | PASS_MNQ |
| min_away_atr=0.12 | 265 | 1.016 | 101 | 2.578 | KILL (WF t<2 or n<30) |
| stop_atr_mult=0.16 | 315 | 1.331 | 124 | 3.2 | KILL (WF t<2 or n<30) |
| stop_atr_mult=0.24 | 275 | 2.97 | 109 | 3.738 | PASS_MNQ |
| entry_end_minutes=528 | 0 | None | 0 | None | KILL (WF t<2 or n<30) |
| entry_end_minutes=792 | 513 | 0.991 | 183 | 2.685 | KILL (WF t<2 or n<30) |

## Leave-one-regime-out (discovery trades)

### quarter

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| 2024Q1 | 58 | 271 | 4.355 |
| 2024Q2 | 50 | 279 | 4.326 |
| 2024Q3 | 52 | 277 | 4.384 |
| 2024Q4 | 53 | 276 | 4.122 |
| 2025Q1 | 48 | 281 | 4.278 |
| 2025Q2 | 30 | 299 | 4.479 |
| 2025Q3 | 38 | 291 | 4.767 |

### atr_tercile

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| na | 329 | 0 | None |

### trend

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| down | 329 | 0 | None |

PASS_MES on thin holdout stays **provisional** until holdout n is healthier or nearby params also pass.