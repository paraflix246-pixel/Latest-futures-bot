# New RTH session strategies — evaluation

Paper / backtest only. Fills: sprint-1 engine (signal-bar close + 1 tick, stop/target on subsequent bars). Clock exits: `time_stop` / `rth_flatten` at close ± 1 tick. Kill rule: walk-forward OOS t < 2 **or** MES fails to replicate.

Holdout uses **pre-registered constructor defaults**, not walk-forward winners.

| Symbol | Strategy | WF folds | WF OOS n | WF OOS PnL | WF t | WF sig | Holdout n | Holdout PnL | Holdout t | Verdict |
|---|---|---:|---:|---:|---:|---|---:|---:|---:|---|
| MES | impulse_clock | 7 | 266 | -7163.37 | -1.915 | False | 100 | -1133.11 | -0.507 | KILLED (walk-forward OOS t<2 or not significant) |
| MNQ | impulse_clock | 7 | 266 | 9338.94 | 2.418 | True | 93 | 5349.16 | 2.542 | KILLED (MES replication failed) |
| MES | last30_momentum | 7 | 120 | -649.35 | -0.401 | False | 65 | -1537.35 | -2.349 | KILLED (walk-forward OOS t<2 or not significant) |
| MNQ | last30_momentum | 7 | 155 | 601.24 | 0.356 | False | 29 | -1052.62 | -2.703 | KILLED (walk-forward OOS t<2 or not significant) |
| MES | orb_break_fade | 7 | 290 | -7586.64 | -1.823 | False | 94 | 647.36 | 0.252 | KILLED (walk-forward OOS t<2 or not significant) |
| MNQ | orb_break_fade | 7 | 223 | -3185.47 | -0.906 | False | 82 | -2484.41 | -1.195 | KILLED (walk-forward OOS t<2 or not significant) |
| MES | orb_crabel | 7 | 122 | -3444.19 | -1.339 | False | 57 | 344.42 | 0.152 | KILLED (walk-forward OOS t<2 or not significant) |
| MNQ | orb_crabel | 7 | 99 | -4607.92 | -2.042 | False | 53 | -1908.29 | -0.991 | KILLED (walk-forward OOS t<2 or not significant) |
| MES | vol_squeeze_expansion | 7 | 44 | -293.07 | -0.234 | False | 25 | -211.1 | -0.212 | KILLED (walk-forward OOS t<2 or not significant) |
| MNQ | vol_squeeze_expansion | 7 | 44 | -3304.65 | -2.771 | False | 29 | 100.19 | 0.098 | KILLED (walk-forward OOS t<2 or not significant) |

**Conclusion: no validated edge.** All five modules killed. MNQ `impulse_clock` cleared t≥2 on that symbol only; MES failed. Crabel-filtered ORB and last-30m momentum (research-spec follow-up) both failed walk-forward t≥2; last-30m holdout was significantly negative on both symbols after costs. Stop; do not spawn EMA variants. Paper / backtest only.
