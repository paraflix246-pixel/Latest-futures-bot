# Harden MES `gap_on_confirm_lock`

Paper / backtest only. Sprint-1 fills. No live trading.

Locked params: `{'confirm_atr': 0.12, 'stop_atr_mult': 0.25}`

- Official WF 180/60: n=36 t=3.656 pnl=3411.47
- Holdout from 2025-09-12: n=140 t=-0.166 pnl=-309.04 overnight=0
- Gate: **PASS_MES**
- Diagnostic WF 90/30 (not the gate): n=84 t=1.846

## Sensitivity (±20% one-factor)

| Variant | WF n | WF t | HO n | HO t | Gate |
|---|---:|---:|---:|---:|---|
| locked | 36 | 3.656 | 140 | -0.166 | PASS_MES |
| confirm_atr=0.096 | 42 | 2.502 | 155 | -0.266 | PASS_MES |
| confirm_atr=0.144 | 30 | 2.991 | 128 | -0.149 | PASS_MES |
| stop_atr_mult=0.2 | 37 | 3.219 | 140 | -0.617 | PASS_MES |
| stop_atr_mult=0.3 | 30 | 3.29 | 140 | -0.407 | PASS_MES |

## Leave-one-regime-out (discovery trades)

### quarter

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| 2024Q3 | 5 | 108 | 1.652 |
| 2024Q4 | 34 | 79 | 1.307 |
| 2025Q1 | 27 | 86 | 1.87 |
| 2025Q2 | 24 | 89 | 0.596 |
| 2025Q3 | 23 | 90 | 1.407 |

### atr_tercile

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| na | 113 | 0 | None |

### trend

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| down | 113 | 0 | None |

PASS_MES on thin holdout stays **provisional** until holdout n is healthier or nearby params also pass.