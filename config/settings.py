"""
Backtester defaults — overridable via CLI flags in scripts/run_backtest.py.
"""
from __future__ import annotations

DEFAULT_ACCOUNT_SIZE = 50_000.0
DEFAULT_RISK_PCT = 0.5          # % of account risked per trade
DEFAULT_TIMEFRAME = "5m"        # 5-minute bars: less noise than 1m, still intraday
DEFAULT_SLIPPAGE_TICKS = 1      # assumed slippage per fill, in ticks (entry AND exit)
DEFAULT_MAX_CONTRACTS = 10      # hard cap so tight stops cannot explode size
DEFAULT_DAILY_LOSS_HALT_PCT = 2.0  # halt new entries after -2% day (sprint overlay)
DEFAULT_COOLDOWN_BARS = 3       # bars to wait after an exit before a new entry

DATA_DIR = "data"
REPORTS_DIR = "reports"

SUPPORTED_SYMBOLS = ["MNQ", "NQ", "MES", "ES"]
SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "1h"]
SUPPORTED_STRATEGIES = [
    "trend", "mean_reversion", "breakout", "ensemble", "vwap_cross", "orb",
    "orb_failure", "vwap_pullback_trend", "vwap_pullback_trend_v2", "regime_bot",
    "vol_expansion_momentum", "extreme_displacement_reversion", "volume_shock_continuation",
    "orb_break_fade", "vol_squeeze_expansion", "impulse_clock",
    "orb_crabel", "last30_momentum", "ib_extension", "on_inventory",
    "lunch_range_break", "vol_gated_ensemble",
    "open_drive", "failed_ib_fade", "afternoon_momentum", "am_vwap_reclaim",
    "orb_filtered", "s2_mes_sens_7", "orb_retrace", "vwap_hour_reclaim_fail",
    "trend15_pullback5",
    "gap_fill_go", "rvol_open15", "vwap_band_fade", "adr_exhaust_fade",
    "pdh_pdl_fail", "morning_reversal",
    "vwap_pullback_cont", "ema_stack_pullback", "ib_mid_fade",
    "three_bar_vwap_fade", "rsi2_vwap_fade", "vwap_reclaim", "vwap_reclaim_90",
    "orb_fail_fade", "gap_and_go", "spread_fade", "nr15_break",
    "wick_reject_cont", "onh_onl_break", "volume_dryup_break",
    "ib_hold_break", "inside_hour_break", "higher_low_vwap", "prior_mid_reclaim",
    "morning_range_break", "keltner_am_fade", "inside_day_orb", "pivot_bounce",
    "vwap_fh_reclaim", "gap_on_range", "open_reject", "gap_on_confirm",
    "gap_on_confirm_lock", "gap_on_fill_only", "am_measured", "vwap_hold_late",
    "cross_lead_open15", "weekday_gap_clock", "vol_clock_fade",
    "gap_on_go_only", "overnight_gap_fade", "first30_fade", "lunch_or_magnet",
    "first5_break",
]

# NQ now has its own real Databento feed (data/NQ_1m.csv, NQ_5m.csv) — no
# longer derived from MNQ. Kept as an empty mapping in case a future symbol
# needs the same derive-from-a-related-instrument fallback.
DERIVED_SYMBOLS: dict[str, str] = {}
