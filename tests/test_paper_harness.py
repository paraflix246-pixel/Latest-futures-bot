"""Paper harness: no live path; replay matches run_backtest."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import pytest

from src.backtest.engine import run_backtest
from src.paper.harness import LiveTradingDisabled, PaperBroker, PaperReplay
from src.strategies.base import StrategySignals


def test_paper_broker_rejects_live():
    with pytest.raises(LiveTradingDisabled):
        PaperBroker(live=True)
    with pytest.raises(LiveTradingDisabled):
        PaperReplay("MNQ", "5m", None, 50_000, 0.5, live=True)


def test_paper_replay_matches_engine_and_writes_intents(tmp_path):
    idx = pd.date_range("2026-01-01", periods=50, freq="5min", tz="UTC")
    closes = np.array([20000] * 30 + [20050 + i * 5 for i in range(20)], dtype=float)
    df = pd.DataFrame(
        {
            "open": closes,
            "high": closes + 1,
            "low": closes - 1,
            "close": closes,
            "volume": np.full(len(closes), 1000),
        },
        index=idx,
    )

    class OneShot:
        name = "one"
        def generate_signals(self, df):
            entries = pd.Series(0, index=df.index)
            stop = pd.Series(np.nan, index=df.index)
            target = pd.Series(np.nan, index=df.index)
            entries.iloc[29] = 1
            stop.iloc[29] = 19950
            target.iloc[29] = 20100
            return StrategySignals(entries=entries, stop_price=stop, target_price=target)

    eng = dict(
        fill_model="next_open",
        apply_exit_slippage=False,
        gap_aware_stops=True,
        trail_update="next_bar",
        cooldown_bars=0,
        allow_same_bar_reentry=False,
        daily_loss_halt_pct=None,
        flatten_at_rth_close=False,
        max_contracts=10,
        slippage_ticks=0,
    )
    direct = run_backtest(df, OneShot(), "MNQ", "5m", 50_000, 0.5, **eng)
    replay = PaperReplay("MNQ", "5m", OneShot(), 50_000, 0.5, engine_kwargs=eng, live=False)
    paper = replay.run(df)
    assert len(paper.trades) == len(direct.trades) == 1
    assert paper.trades[0].pnl == direct.trades[0].pnl
    assert len(replay.broker.intents) == 1
    log = tmp_path / "paper.json"
    replay.write_log(paper, log)
    text = log.read_text()
    assert '"live": false' in text
    assert "Paper/backtest" in text
