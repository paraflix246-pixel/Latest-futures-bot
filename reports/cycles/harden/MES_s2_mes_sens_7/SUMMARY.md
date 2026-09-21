# Harden MES `s2_mes_sens_7`

Paper / backtest only. Sprint-1 fills. No live trading.

Locked params: `{'or_minutes': 15, 'entry_window_minutes': 130, 'volume_mult': 1.4, 'require_vwap_align': True, 'skip_inside_overnight': True, 'require_retest': False, 'target_r': 1.0, 'stop_mode': 'mid'}`

- Official WF 180/60: n=39 t=0.414 pnl=535.0
- Holdout from 2025-09-12: n=41 t=-0.073 pnl=-88.24 overnight=0
- Gate: **KILL (WF t<2 or n<30)**
- Diagnostic WF 90/30 (not the gate): n=65 t=1.022

## Sensitivity (±20% one-factor)

| Variant | WF n | WF t | HO n | HO t | Gate |
|---|---:|---:|---:|---:|---|
| locked | 39 | 0.414 | 41 | -0.073 | KILL (WF t<2 or n<30) |
| or_minutes=12 | 39 | 0.414 | 41 | -0.073 | KILL (WF t<2 or n<30) |
| or_minutes=18 | 37 | -0.348 | 37 | -0.283 | KILL (WF t<2 or n<30) |
| entry_window_minutes=104 | 37 | 0.462 | 37 | -0.251 | KILL (WF t<2 or n<30) |
| entry_window_minutes=156 | 40 | 0.428 | 41 | -0.073 | KILL (WF t<2 or n<30) |
| volume_mult=1.12 | 46 | 1.12 | 96 | -1.555 | KILL (WF t<2 or n<30) |
| volume_mult=1.68 | 31 | 0.285 | 20 | 0.204 | KILL (WF t<2 or n<30) |
| target_r=0.8 | 39 | -0.2 | 41 | -0.191 | KILL (WF t<2 or n<30) |
| target_r=1.2 | 39 | 0.075 | 41 | 0.145 | KILL (WF t<2 or n<30) |

## Leave-one-regime-out (discovery trades)

### quarter

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| 2024Q3 | 2 | 82 | 0.937 |
| 2024Q4 | 17 | 67 | 0.409 |
| 2025Q1 | 18 | 66 | -0.083 |
| 2025Q2 | 32 | 52 | 1.49 |
| 2025Q3 | 15 | 69 | 0.419 |

### atr_tercile

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| na | 84 | 0 | None |

### trend

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| down | 84 | 0 | None |

PASS_MES on thin holdout stays **provisional** until holdout n is healthier or nearby params also pass.