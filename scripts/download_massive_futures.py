#!/usr/bin/env python
"""
Ingest Massive Futures REST aggregates for MNQ + MES (NQ/ES fallback).

Pulls per-contract 1m/5m bars, rolls a volume-priority front month, writes
loader-compatible CSVs under data/. Never prints MASSIVE_API_KEY.

Usage:
    python scripts/download_massive_futures.py --probe
    python scripts/download_massive_futures.py --start 2020-01-01 --resolutions 5min
    python scripts/download_massive_futures.py --start 2020-01-01 --resolutions 1min 5min --promote

Auth for future pulls: Authorization: Bearer $MASSIVE_API_KEY against
https://api.massive.com/futures/v1/aggs/{ticker}?resolution=5min&...
Tickers like MNQU5 / MESU5 / ESU5 work. `product_code` on /contracts is
flaky — this script enumerates H/M/U/Z (+ optional 2-digit year) instead.

Attached research dumps live in data/massive/*.csv.gz and are preferred
by the loader. Do not block research on a cloud-env key when those exist.

If MASSIVE_API_KEY is missing and no dump is present, exits 2 and writes
reports/massive/BLOCKER.md.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.massive_client import (  # noqa: E402
    MassiveAuthError,
    MassiveFuturesClient,
    MissingMassiveApiKey,
    enumerate_hmuz_tickers,
    infer_hmuz_last_trade,
)
from src.data.roll_continuous import (  # noqa: E402
    backward_ratio_adjust,
    pick_front_month,
    to_loader_csv,
)

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "massive_raw"
DATA_DIR = ROOT / "data"
REPORT_DIR = ROOT / "reports" / "massive"
PRODUCTS = ["MNQ", "MES"]
FALLBACK_PRODUCTS = ["NQ", "ES"]
RES_TO_TF = {"1min": "1m", "5min": "5m", "1m": "1m", "5m": "5m"}
TF_TO_RES = {"1m": "1min", "5m": "5min"}


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--start", default="2020-01-01")
    p.add_argument("--end", default=None, help="YYYY-MM-DD inclusive (default: today UTC)")
    p.add_argument("--products", nargs="+", default=PRODUCTS)
    p.add_argument("--resolutions", nargs="+", default=["5min"], choices=["1min", "5min", "1m", "5m"])
    p.add_argument("--probe", action="store_true", help="Auth-only probe; do not download")
    p.add_argument(
        "--plan-depth",
        action="store_true",
        help="Cheap 1session probes of 2022–2025 tickers to measure history depth. Never prints the key.",
    )
    p.add_argument("--promote", action="store_true", help="Overwrite data/{SYM}_{tf}.csv if longer")
    p.add_argument("--min-days-to-expiry", type=int, default=5)
    return p.parse_args()


def _write_blocker(kind: str, detail: str) -> None:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    text = (
        "# Massive ingest blocker\n\n"
        "Paper / backtest only. No live trading.\n\n"
        f"**Kind:** `{kind}`\n\n"
        f"**Detail:** {detail}\n\n"
        "Founder action: set `MASSIVE_API_KEY` in the Cloud Agent / machine "
        "environment (never commit it). Futures history depth depends on the "
        "Massive plan (Basic/Starter ≈ 2y, Developer ≈ 5y, Advanced = full "
        "history back to 2017-04-03).\n"
    )
    (REPORT_DIR / "BLOCKER.md").write_text(text)
    payload = {
        "ok": False,
        "kind": kind,
        "detail": detail,
        "has_env_key": bool(os.environ.get("MASSIVE_API_KEY", "").strip()),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    (REPORT_DIR / "ingest_status.json").write_text(json.dumps(payload, indent=2))


def _aggs_to_frame(rows: List[Dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["datetime", "open", "high", "low", "close", "volume"])
    recs = []
    for r in rows:
        ws = r.get("window_start")
        if ws is None:
            continue
        # Massive documents nanosecond unix timestamps.
        ts = pd.to_datetime(int(ws), utc=True, unit="ns")
        recs.append(
            {
                "datetime": ts,
                "open": r.get("open"),
                "high": r.get("high"),
                "low": r.get("low"),
                "close": r.get("close"),
                "volume": r.get("volume") or 0,
                "ticker": r.get("ticker"),
            }
        )
    df = pd.DataFrame(recs).dropna(subset=["open", "high", "low", "close"])
    return df.sort_values("datetime").drop_duplicates("datetime", keep="last")


def _existing_span(symbol: str, tf: str) -> Dict[str, Any]:
    path = DATA_DIR / f"{symbol}_{tf}.csv"
    if not path.exists():
        return {"exists": False, "rows": 0}
    df = pd.read_csv(path, parse_dates=["datetime"])
    return {
        "exists": True,
        "rows": int(len(df)),
        "start": str(df["datetime"].min()),
        "end": str(df["datetime"].max()),
        "path": str(path),
    }


def main() -> int:
    args = parse_args()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    resolutions = [TF_TO_RES.get(r, r) for r in args.resolutions]
    end = args.end or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    try:
        client = MassiveFuturesClient()
    except MissingMassiveApiKey as exc:
        _write_blocker("missing_api_key", str(exc))
        print(str(exc), file=sys.stderr)
        return 2

    try:
        probe = client.probe_auth()
    except (MassiveAuthError, Exception) as exc:
        _write_blocker("auth_failed", str(exc))
        print(f"Massive auth failed: {exc}", file=sys.stderr)
        return 2

    probe_payload = {
        "ok": True,
        "auth_style": probe.style,
        "status_code": probe.status_code,
        "has_env_key": True,
        "start": args.start,
        "end": end,
        "products": args.products,
        "resolutions": resolutions,
        "ts": datetime.now(timezone.utc).isoformat(),
        "auth_probes": [
            {"style": p.style, "status_code": p.status_code, "ok": p.ok}
            for p in client.auth_probes
        ],
    }
    (REPORT_DIR / "ingest_status.json").write_text(json.dumps(probe_payload, indent=2))
    print(f"Massive auth ok via {probe.style} (HTTP {probe.status_code})")
    if args.probe:
        return 0
    if args.plan_depth:
        return _plan_depth(client, end)

    summary: Dict[str, Any] = {"auth": probe_payload, "symbols": {}}
    for product in args.products:
        print(f"Enumerating HMUZ contracts for {product} ...", flush=True)
        tickers = enumerate_hmuz_tickers(product, args.start, end)
        contracts: List[Dict[str, Any]] = []
        try:
            listed = client.list_contracts(product_code=product, type_="single")
            by_ticker = {c.get("ticker"): c for c in listed if c.get("ticker")}
            from src.data.massive_client import infer_hmuz_last_trade as _infer

            for t in tickers:
                inferred = _infer(t, year_hint=int(end[:4]))
                if t in by_ticker:
                    row = dict(by_ticker[t])
                    if not row.get("last_trade_date") and inferred:
                        row["last_trade_date"] = inferred
                    contracts.append(row)
                else:
                    contracts.append({"ticker": t, "last_trade_date": inferred})
        except Exception as exc:
            print(f"  contracts endpoint skipped ({exc}); using HMUZ names only", flush=True)
            from src.data.massive_client import infer_hmuz_last_trade as _infer

            contracts = [
                {"ticker": t, "last_trade_date": _infer(t, year_hint=int(end[:4]))}
                for t in tickers
            ]
        (RAW_DIR / f"{product}_contracts.json").write_text(json.dumps(contracts, indent=2, default=str))
        print(f"  {len(contracts)} HMUZ names", flush=True)

        for resolution in resolutions:
            tf = RES_TO_TF[resolution]
            frames = {}
            for i, c in enumerate(contracts):
                ticker = c.get("ticker")
                if not ticker:
                    continue
                print(f"  [{i+1}/{len(contracts)}] {ticker} {resolution}", flush=True)
                try:
                    rows = client.list_aggregates(
                        ticker,
                        resolution=resolution,
                        window_start_gte=args.start,
                        window_start_lte=end,
                    )
                except Exception as exc:
                    print(f"    skip {ticker}: {exc}", flush=True)
                    continue
                df = _aggs_to_frame(rows)
                if df.empty:
                    continue
                raw_path = RAW_DIR / f"{ticker}_{tf}.csv"
                df.to_csv(raw_path, index=False)
                frames[ticker] = df
            if not frames:
                print(f"  no bars downloaded for {product} {resolution}", flush=True)
                continue
            raw, rolls = pick_front_month(frames, contracts, min_days_to_expiry=args.min_days_to_expiry)
            adj = backward_ratio_adjust(raw, rolls)
            out = to_loader_csv(adj)
            dest = DATA_DIR / f"{product}_{tf}.csv"
            staging = DATA_DIR / f"{product}_{tf}_massive.csv"
            out.to_csv(staging, index=False)
            roll_path = REPORT_DIR / f"{product}_{tf}_rolls.json"
            roll_path.write_text(
                json.dumps(
                    [
                        {
                            "timestamp": str(r.timestamp),
                            "from": r.from_ticker,
                            "to": r.to_ticker,
                            "from_close": r.from_close,
                            "to_close": r.to_close,
                            "ratio": r.ratio,
                        }
                        for r in rolls
                    ],
                    indent=2,
                )
            )
            existing = _existing_span(product, tf)
            promoted = False
            if args.promote:
                if (not existing.get("exists")) or len(out) > int(existing.get("rows") or 0):
                    out.to_csv(dest, index=False)
                    promoted = True
            summary["symbols"][f"{product}_{tf}"] = {
                "contracts_used": len(frames),
                "rows": int(len(out)),
                "start": str(out["datetime"].min()),
                "end": str(out["datetime"].max()),
                "rolls": len(rolls),
                "staging": str(staging),
                "promoted": promoted,
                "existing": existing,
            }
            print(
                f"  wrote {staging} rows={len(out)} "
                f"{out['datetime'].min()} -> {out['datetime'].max()} rolls={len(rolls)}",
                flush=True,
            )

    if not summary["symbols"]:
        if args.products == PRODUCTS:
            print("Primary micros empty; founder may need NQ/ES product codes.", flush=True)
        _write_blocker(
            "empty_download",
            "Auth succeeded but no usable MNQ/MES (or requested product) bars "
            "were returned. Plan history may be too short, or product codes "
            f"differ from {args.products}.",
        )
        (REPORT_DIR / "ingest_status.json").write_text(json.dumps(summary, indent=2, default=str))
        return 3

    summary["ok"] = True
    (REPORT_DIR / "ingest_status.json").write_text(json.dumps(summary, indent=2, default=str))
    return 0


def _plan_depth(client: MassiveFuturesClient, end: str) -> int:
    """1session probes. Writes reports/massive/PLAN_DEPTH.md. Never logs the key."""
    tickers = [
        "MNQU5", "MNQZ4", "MNQH4", "MNQZ3", "MNQH3", "MNQZ2", "MNQH2",
        "MESU5", "MESZ3", "MESH3",
    ]
    rows = []
    for ticker in tickers:
        try:
            bars = client.list_aggregates(
                ticker,
                resolution="1session",
                window_start_gte="2017-01-01",
                window_start_lte=end,
                limit=50,
                sort="window_start.asc",
            )
            n = len(bars)
            first = bars[0].get("session_end_date") if bars else None
            last = bars[-1].get("session_end_date") if bars else None
            err = None
        except Exception as exc:
            n, first, last, err = 0, None, None, type(exc).__name__
        rows.append({"ticker": ticker, "n": n, "first": first, "last": last, "error": err})
        print(f"  {ticker}: n={n} first={first} last={last} err={err}", flush=True)

    nonempty = [r for r in rows if r["n"] > 0]
    earliest = min((r["first"] for r in nonempty if r["first"]), default=None)
    kind = "plan_history_2y" if (earliest and earliest >= "2024-01-01") else (
        "has_pre_2024" if earliest and earliest < "2024-01-01" else "empty_or_rate_limited"
    )
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Massive plan-depth probe",
        "",
        "Paper / backtest only. Key read from `os.environ['MASSIVE_API_KEY']` only; never printed.",
        "",
        f"Generated: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        f"**Kind:** `{kind}`",
        f"**Earliest session_end_date among nonempty probes:** `{earliest}`",
        "",
        "Massive published history: Basic/Starter = 2 years, Developer = 5 years, Advanced = 2017-04-03.",
        "A 2-year window from 2026-09-21 starts ~2024-09-21, matching the attached gzip dumps.",
        "",
        "| Ticker | n (1session pages) | first | last | error |",
        "|---|---:|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['ticker']} | {r['n']} | {r['first']} | {r['last']} | {r['error'] or ''} |")
    lines.extend(
        [
            "",
            "Do not fabricate bars. If 2022–2023 tickers are empty, the tape cannot thicken on this plan.",
            "",
        ]
    )
    (REPORT_DIR / "PLAN_DEPTH.md").write_text("\n".join(lines))
    (REPORT_DIR / "plan_depth.json").write_text(json.dumps({"kind": kind, "earliest": earliest, "rows": rows}, indent=2))
    print(f"Wrote {REPORT_DIR / 'PLAN_DEPTH.md'} kind={kind} earliest={earliest}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
