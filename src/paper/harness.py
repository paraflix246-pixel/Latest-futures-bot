"""
Paper-only replay harness.

Replays historical (or streaming-fed) OHLCV bars through the same realistic
backtest engine used in research. There is no broker socket, no credentials,
and `live=True` raises. This is a fill-audit / paper log tool, not a trader.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

from src.backtest.engine import BacktestResult, Trade, run_backtest
from src.strategies.base import Strategy


class LiveTradingDisabled(RuntimeError):
    """Raised if anything tries to turn this harness into a live path."""


class PaperBroker:
    """Order blotter that never leaves the process.

    `submit_market` records an intent. It does not call Rithmic, MT5,
    TradersPost, or any network API.
    """

    def __init__(self, live: bool = False) -> None:
        if live:
            raise LiveTradingDisabled(
                "Paper harness cannot enable live trading. Paper/backtest only."
            )
        self.intents: list[dict] = []

    def submit_market(
        self,
        symbol: str,
        direction: int,
        contracts: int,
        reason: str,
        timestamp: pd.Timestamp,
    ) -> dict:
        intent = {
            "symbol": symbol,
            "direction": int(direction),
            "contracts": int(contracts),
            "reason": reason,
            "timestamp": str(timestamp),
            "venue": "paper_replay",
        }
        self.intents.append(intent)
        return intent


class PaperReplay:
    """Run a strategy over a bar series with the research engine, log as paper."""

    def __init__(
        self,
        symbol: str,
        timeframe: str,
        strategy: Strategy,
        account_size: float,
        risk_pct: float,
        engine_kwargs: Optional[Dict[str, Any]] = None,
        live: bool = False,
    ) -> None:
        if live:
            raise LiveTradingDisabled(
                "PaperReplay refuses live=True. Use historical bars only."
            )
        self.symbol = symbol
        self.timeframe = timeframe
        self.strategy = strategy
        self.account_size = account_size
        self.risk_pct = risk_pct
        self.engine_kwargs = dict(engine_kwargs or {})
        self.broker = PaperBroker(live=False)

    def run(self, df: pd.DataFrame) -> BacktestResult:
        result = run_backtest(
            df=df,
            strategy=self.strategy,
            symbol=self.symbol,
            timeframe=self.timeframe,
            account_size=self.account_size,
            risk_pct=self.risk_pct,
            **self.engine_kwargs,
        )
        for t in result.trades:
            self.broker.submit_market(
                symbol=t.symbol,
                direction=t.direction,
                contracts=t.contracts,
                reason=f"paper_fill:{t.exit_reason}",
                timestamp=t.entry_time,
            )
        return result

    def write_log(self, result: BacktestResult, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "mode": "paper",
            "live": False,
            "symbol": result.symbol,
            "strategy": result.strategy,
            "timeframe": result.timeframe,
            "account_size": self.account_size,
            "disclaimer": (
                "Paper/backtest replay only. Not a live session. "
                "Fills are modeled, not exchange prints. No broker credentials used."
            ),
            "trade_count": len(result.trades),
            "final_equity": float(result.equity_curve.iloc[-1]) if len(result.equity_curve) else self.account_size,
            "trades": [_trade_dict(t) for t in result.trades],
            "intents": self.broker.intents,
        }
        path.write_text(json.dumps(payload, indent=2, default=str))


def _trade_dict(t: Trade) -> dict:
    d = asdict(t)
    d["entry_time"] = str(t.entry_time)
    d["exit_time"] = str(t.exit_time)
    return d
