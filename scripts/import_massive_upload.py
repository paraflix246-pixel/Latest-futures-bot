#!/usr/bin/env python
"""Copy a founder-provided Massive 5m dump into data/massive/*.csv.gz.

Accepts either the canonical name (MNQ_5m.csv) or an upload suffix
(MNQ_5m_1cd3.csv). Does not print secrets. Paper / backtest only.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / "data" / "massive"


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("paths", nargs="+", help="Uploaded Massive CSVs")
    return p.parse_args()


def _symbol_from_name(path: Path) -> str:
    name = path.name.upper()
    for sym in ("MNQ", "MES", "NQ", "ES"):
        if name.startswith(sym):
            return sym
    raise SystemExit(f"Cannot infer symbol from {path.name}")


def main() -> None:
    args = parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    for raw in args.paths:
        src = Path(raw)
        if not src.exists():
            raise SystemExit(f"missing {src}")
        symbol = _symbol_from_name(src)
        df = pd.read_csv(src)
        if "timestamp" not in df.columns and "datetime" not in df.columns:
            raise SystemExit(f"{src} has no timestamp/datetime column")
        out = DEST / f"{symbol}_5m.csv.gz"
        df.to_csv(out, index=False, compression="gzip")
        print(f"wrote {out} rows={len(df)} bytes={out.stat().st_size}")


if __name__ == "__main__":
    main()
