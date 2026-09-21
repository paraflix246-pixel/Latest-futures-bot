# Bar vs clock (MNQ discovery)

Paper / backtest only. Sprint-1 fills. No live trading.

Verdict: **NOT_IN_CLOCK_OR_BARS_YET**

| Baseline | n | t | PnL | Gate |
|---|---:|---:|---:|---|
| clock_long_rth | 325 | -0.722 | -2046.24 | no |
| clock_short_rth | 334 | 0.048 | 138.69 | no |
| tue_thu_long | 194 | -1.762 | -3831.06 | no |
| mon_fri_long | 131 | 1.177 | 2097.63 | no |

CLOCK_EDGE means a weekday/time-of-day long/short cleared t>=2 without a candlestick pattern. Otherwise MNQ 1m OHLCV on this 2024–now tape has not shown a kill-gate edge from calendar either.
