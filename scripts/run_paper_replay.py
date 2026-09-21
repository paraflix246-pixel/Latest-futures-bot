#!/usr/bin/env python
"""
Paper replay: run a strategy over historical bars with the realistic engine.

This is NOT live trading. There is no --live flag. No broker is contacted.

Example:
    python scripts/run_paper_replay.py --symbol MNQ --timeframe 5m --strategy ensemble \
        --start 2025-09-12
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import (  # noqa: E402
    DEFAULT_ACCOUNT_SIZE,
    DEFAULT_RISK_PCT,
    DEFAULT_TIMEFRAME,
    REPORTS_DIR,
    SUPPORTED_STRATEGIES,
    SUPPORTED_SYMBOLS,
    SUPPORTED_TIMEFRAMES,
)
from src.backtest.metrics import compute_metrics  # noqa: E402
from src.data.loader import load_ohlcv, slice_range  # noqa: E402
from src.paper.harness import PaperReplay  # noqa: E402
from src.strategies import get_strategy  # noqa: E402

# Same overlay as sprint-1 "after" (realistic fills, hard risk).
PAPER_ENGINE = dict(
    fill_model="next_open",
    apply_exit_slippage=True,
    gap_aware_stops=True,
    trail_update="next_bar",
    cooldown_bars=3,
    allow_same_bar_reentry=False,
    daily_loss_halt_pct=2.0,
    flatten_at_rth_close=True,
    max_contracts=10,
)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--symbol", required=True, choices=SUPPORTED_SYMBOLS)
    p.add_argument("--timeframe", default=DEFAULT_TIMEFRAME, choices=SUPPORTED_TIMEFRAMES)
    p.add_argument("--strategy", required=True, choices=SUPPORTED_STRATEGIES)
    p.add_argument("--start", default=None)
    p.add_argument("--end", default=None)
    p.add_argument("--account-size", type=float, default=DEFAULT_ACCOUNT_SIZE)
    p.add_argument("--risk-pct", type=float, default=DEFAULT_RISK_PCT)
    p.add_argument("--out", default=None, help="JSON log path (default reports/paper/...)")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    df = load_ohlcv(args.symbol, args.timeframe)
    df = slice_range(df, args.start, args.end)
    if df.empty:
        raise SystemExit("No bars in range")

    replay = PaperReplay(
        symbol=args.symbol,
        timeframe=args.timeframe,
        strategy=get_strategy(args.strategy),
        account_size=args.account_size,
        risk_pct=args.risk_pct,
        engine_kwargs=PAPER_ENGINE,
        live=False,
    )
    result = replay.run(df)
    metrics = compute_metrics(result, args.account_size)

    out = Path(args.out) if args.out else (
        Path(__file__).resolve().parent.parent
        / REPORTS_DIR
        / "paper"
        / f"{args.symbol}_{args.timeframe}_{args.strategy}_replay.json"
    )
    replay.write_log(result, out)
    print("PAPER REPLAY ONLY — not live, no broker.")
    print(json.dumps(metrics, indent=2))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
