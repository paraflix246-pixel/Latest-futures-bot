# Harden MNQ `vwap_reclaim_90_lock`

Paper / backtest only. Sprint-1 fills. No live trading.

Locked params: `{'min_away_atr': 0.1, 'stop_atr_mult': 0.3, 'entry_end_minutes': 660, 'first_hour_bias': True}`

- Official WF 180/60: n=259 t=3.943 pnl=10093.72
- Holdout from 2025-09-12: n=87 t=3.696 pnl=4892.52 overnight=0
- Gate: **PASS_MNQ**
- Diagnostic WF 90/30 (not the gate): n=376 t=4.462

## Sensitivity (±20% one-factor)

| Variant | WF n | WF t | HO n | HO t | Gate |
|---|---:|---:|---:|---:|---|
| locked | 259 | 3.943 | 87 | 3.696 | PASS_MNQ |
| min_away_atr=0.08 | 287 | 4.967 | 100 | 4.037 | PASS_MNQ |
| min_away_atr=0.12 | 233 | 3.171 | 75 | 3.874 | PASS_MNQ |
| stop_atr_mult=0.24 | 275 | 2.97 | 109 | 3.738 | PASS_MNQ |
| stop_atr_mult=0.36 | 229 | 4.014 | 47 | 2.032 | PASS_MNQ |
| entry_end_minutes=528 | 0 | None | 0 | None | KILL (WF t<2 or n<30) |
| entry_end_minutes=792 | 453 | 2.906 | 145 | 3.047 | PASS_MNQ |

## Leave-one-regime-out (discovery trades)

### quarter

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| 2024Q1 | 51 | 235 | 5.993 |
| 2024Q2 | 44 | 242 | 5.416 |
| 2024Q3 | 45 | 241 | 4.869 |
| 2024Q4 | 48 | 238 | 5.427 |
| 2025Q1 | 41 | 245 | 4.844 |
| 2025Q2 | 19 | 267 | 5.793 |
| 2025Q3 | 38 | 248 | 5.791 |

### atr_tercile

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| na | 286 | 0 | None |

### trend

| Left out | n left out | remaining n | remaining t |
|---|---:|---:|---:|
| down | 286 | 0 | None |

PASS_MES on thin holdout stays **provisional** until holdout n is healthier or nearby params also pass.

## Cost ×2 and holdout bootstrap

Slippage 1 → 2 ticks. Paper/backtest only.

| Check | n | t | PnL |
|---|---:|---:|---|
| Cost×2 WF 180/60 | 258 | **3.776** | +$9605, 7/7 folds |
| Cost×2 holdout | 86 | **3.964** | +$5073 |
| Holdout bootstrap 2000 draws | 87 | mean t=3.741 | 95% CI **[1.612, 5.967]**, frac t≥2 = **95%**, frac t>0 = **100%** |

`entry_end_minutes=528` is an invalid ±20% (08:48 ET, before cash open) and is ignored. Valid one-factor neighbors: **5/5 PASS_MNQ**.

Quarter LORO remaining t all ≥4.84. ATR tercile / trend LORO are all-na (date vs Timestamp diagnostic), not a kill.

**READY_FOR_PAPER_LIVE_CANDIDATE** with caveats: 1m tape holdout ends 2026-03-11; `max_hold_bars=36` is 36 minutes; bootstrap CI lower bound is 1.61 (above 0, below 2). **No live trading.**
