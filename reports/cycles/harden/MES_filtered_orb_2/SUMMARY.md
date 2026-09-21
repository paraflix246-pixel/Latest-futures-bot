# Harden MES `filtered_orb_2`

Paper / backtest only. Sprint-1 fills. No live trading.

Locked params: `{'or_minutes': 15, 'entry_window_minutes': 120, 'volume_mult': 1.3, 'require_vwap_align': True, 'skip_inside_overnight': True, 'require_retest': False, 'target_r': 1.0}`

- Official WF 180/60: n=42 t=0.366 pnl=480.02
- Holdout from 2025-09-12: n=55 t=-0.854 pnl=-1251.79 overnight=0
- Gate: **KILL (WF t<2 or n<30)**
- Diagnostic WF 90/30 (not the gate): n=76 t=0.845

## Sensitivity (±20% one-factor)

| Variant | WF n | WF t | HO n | HO t | Gate |
|---|---:|---:|---:|---:|---|
| locked | 42 | 0.366 | 55 | -0.854 | KILL (WF t<2 or n<30) |
| or_minutes=12 | 42 | 0.366 | 55 | -0.854 | KILL (WF t<2 or n<30) |
| or_minutes=18 | 40 | 0.38 | 49 | 0.415 | KILL (WF t<2 or n<30) |
| entry_window_minutes=96 | 38 | 0.175 | 53 | -0.999 | KILL (WF t<2 or n<30) |
| entry_window_minutes=144 | 42 | 0.366 | 57 | -0.834 | KILL (WF t<2 or n<30) |
| volume_mult=1.04 | 50 | 0.941 | 108 | -1.566 | KILL (WF t<2 or n<30) |
| volume_mult=1.56 | 32 | 1.024 | 23 | 0.112 | KILL (WF t<2 or n<30) |
| target_r=0.8 | 42 | -0.127 | 55 | -0.553 | KILL (WF t<2 or n<30) |
| target_r=1.2 | 42 | 0.056 | 55 | -0.488 | KILL (WF t<2 or n<30) |

## Leave-one-regime-out (discovery trades)

### quarter

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| 2024Q3 | 2 | 98 | 0.429 |
| 2024Q4 | 21 | 79 | 0.139 |
| 2025Q1 | 24 | 76 | -0.644 |
| 2025Q2 | 35 | 65 | 0.838 |
| 2025Q3 | 18 | 82 | 0.168 |

### atr_tercile

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| na | 100 | 0 | None |

### trend

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| down | 100 | 0 | None |

PASS_MES on thin holdout stays **provisional** until holdout n is healthier or nearby params also pass.