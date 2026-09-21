"""Locked research protocol: sprint-1 realistic engine + kill-gate constants.

Do not change these to 'find' an edge. Live trading stays disabled.
"""
from __future__ import annotations

from typing import Any, Dict

from src.backtest.engine import ENGINE_DEFAULTS

# Sprint-1 "after" overlays (reports/sprint1). Realistic fills, RTH flatten.
SPRINT1_AFTER_ENGINE: Dict[str, Any] = dict(ENGINE_DEFAULTS)
SPRINT1_AFTER_ENGINE.update(
    {
        "fill_model": "next_open",
        "apply_exit_slippage": True,
        "gap_aware_stops": True,
        "trail_update": "next_bar",
        "cooldown_bars": 3,
        "allow_same_bar_reentry": False,
        "daily_loss_halt_pct": 2.0,
        "flatten_at_rth_close": True,
        "max_contracts": 10,
        "rth_entries_only": True,
    }
)

KILL_T_STAT = 2.0
KILL_MIN_TRADES = 30
WF_TRAIN_DAYS = 180
WF_TEST_DAYS = 60
ACCOUNT_SIZE = 50_000.0
RISK_PCT = 0.5
HOLDOUT_OOS_START = "2025-09-12"  # locked with sprint-1; never used to pick params
PRIMARY = "MNQ"
REPLICATION = "MES"
