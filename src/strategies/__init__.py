from src.strategies.afternoon_momentum import AfternoonMomentumStrategy
from src.strategies.am_vwap_reclaim import AmVwapReclaimStrategy
from src.strategies.breakout import BreakoutStrategy
from src.strategies.failed_ib_fade import FailedIbFadeStrategy
from src.strategies.ensemble import EnsembleStrategy
from src.strategies.extreme_displacement_reversion import ExtremeDisplacementReversionStrategy
from src.strategies.ib_extension import IbExtensionStrategy
from src.strategies.impulse_clock import ImpulseClockStrategy
from src.strategies.last30_momentum import Last30MomentumStrategy
from src.strategies.lunch_range_break import LunchRangeBreakStrategy
from src.strategies.mean_reversion import MeanReversionStrategy
from src.strategies.on_inventory import OnInventoryStrategy
from src.strategies.open_drive import OpenDriveStrategy
from src.strategies.orb_filtered import MesSens7Strategy, OrbFilteredStrategy
from src.strategies.orb_retrace import OrbRetraceStrategy
from src.strategies.orb_fail_fade import OrbFailFadeStrategy
from src.strategies.gap_and_go import GapAndGoStrategy
from src.strategies.spread_fade import SpreadFadeStrategy
from src.strategies.nr15_break import Nr15BreakStrategy
from src.strategies.wick_reject_cont import WickRejectContStrategy
from src.strategies.onh_onl_break import OnhOnlBreakStrategy
from src.strategies.volume_dryup_break import VolumeDryupBreakStrategy
from src.strategies.ib_hold_break import IbHoldBreakStrategy
from src.strategies.inside_hour_break import InsideHourBreakStrategy
from src.strategies.higher_low_vwap import HigherLowVwapStrategy
from src.strategies.prior_mid_reclaim import PriorMidReclaimStrategy
from src.strategies.morning_range_break import MorningRangeBreakStrategy
from src.strategies.keltner_am_fade import KeltnerAmFadeStrategy
from src.strategies.inside_day_orb import InsideDayOrbStrategy
from src.strategies.pivot_bounce import PivotBounceStrategy
from src.strategies.trend15_pullback5 import Trend15Pullback5Strategy
from src.strategies.vwap_hour import VwapHourReclaimFailStrategy
from src.strategies.vwap_first_hour import VwapFirstHourStrategy
from src.strategies.gap_on_range import GapOnRangeStrategy
from src.strategies.open_reject import OpenRejectStrategy
from src.strategies.gap_on_confirm import GapOnConfirmStrategy
from src.strategies.am_measured import AmMeasuredMoveStrategy
from src.strategies.vwap_hold_late import VwapHoldLateStrategy
from src.strategies.gap_fill_go import GapFillGoStrategy
from src.strategies.rvol_open15 import RvolOpen15Strategy
from src.strategies.vwap_band_fade import VwapBandFadeStrategy
from src.strategies.adr_exhaust_fade import AdrExhaustFadeStrategy
from src.strategies.pdh_pdl_fail import PdhPdlFailStrategy
from src.strategies.morning_reversal import MorningReversalStrategy
from src.strategies.vwap_pullback_cont import VwapPullbackContStrategy
from src.strategies.ema_stack_pullback import EmaStackPullbackStrategy
from src.strategies.ib_mid_fade import IbMidFadeStrategy
from src.strategies.three_bar_vwap_fade import ThreeBarVwapFadeStrategy
from src.strategies.rsi2_vwap_fade import Rsi2VwapFadeStrategy
from src.strategies.vwap_reclaim import VwapReclaimStrategy
from src.strategies.opening_range_breakout import OpeningRangeBreakoutStrategy
from src.strategies.orb_break_fade import OrbBreakFadeStrategy
from src.strategies.orb_crabel import OrbCrabelStrategy
from src.strategies.orb_failure import OrbFailureStrategy
from src.strategies.trend_following import TrendFollowingStrategy
from src.strategies.vol_expansion_momentum import VolExpansionMomentumStrategy
from src.strategies.vol_gated_ensemble import VolGatedEnsembleStrategy
from src.strategies.vol_squeeze_expansion import VolSqueezeExpansionStrategy
from src.strategies.volume_shock_continuation import VolumeShockContinuationStrategy
from src.strategies.vwap_ema_cross import VwapEmaCrossStrategy
from src.strategies.vwap_pullback_trend import VwapPullbackTrendStrategy
from src.strategies.vwap_pullback_trend_v2 import VwapPullbackTrendV2Strategy

STRATEGIES = {
    "trend": TrendFollowingStrategy,
    "mean_reversion": MeanReversionStrategy,
    "breakout": BreakoutStrategy,
    "ensemble": EnsembleStrategy,
    "vwap_cross": VwapEmaCrossStrategy,
    "orb": OpeningRangeBreakoutStrategy,
    "orb_failure": OrbFailureStrategy,
    "vwap_pullback_trend": VwapPullbackTrendStrategy,
    "vwap_pullback_trend_v2": VwapPullbackTrendV2Strategy,
    "vol_expansion_momentum": VolExpansionMomentumStrategy,
    "extreme_displacement_reversion": ExtremeDisplacementReversionStrategy,
    "volume_shock_continuation": VolumeShockContinuationStrategy,
    "orb_break_fade": OrbBreakFadeStrategy,
    "vol_squeeze_expansion": VolSqueezeExpansionStrategy,
    "impulse_clock": ImpulseClockStrategy,
    "orb_crabel": OrbCrabelStrategy,
    "last30_momentum": Last30MomentumStrategy,
    "ib_extension": IbExtensionStrategy,
    "on_inventory": OnInventoryStrategy,
    "lunch_range_break": LunchRangeBreakStrategy,
    "vol_gated_ensemble": VolGatedEnsembleStrategy,
    "open_drive": OpenDriveStrategy,
    "failed_ib_fade": FailedIbFadeStrategy,
    "afternoon_momentum": AfternoonMomentumStrategy,
    "am_vwap_reclaim": AmVwapReclaimStrategy,
    "orb_filtered": OrbFilteredStrategy,
    "s2_mes_sens_7": MesSens7Strategy,
    "orb_retrace": OrbRetraceStrategy,
    "orb_fail_fade": OrbFailFadeStrategy,
    "gap_and_go": GapAndGoStrategy,
    "spread_fade": SpreadFadeStrategy,
    "nr15_break": Nr15BreakStrategy,
    "wick_reject_cont": WickRejectContStrategy,
    "onh_onl_break": OnhOnlBreakStrategy,
    "volume_dryup_break": VolumeDryupBreakStrategy,
    "ib_hold_break": IbHoldBreakStrategy,
    "inside_hour_break": InsideHourBreakStrategy,
    "higher_low_vwap": HigherLowVwapStrategy,
    "prior_mid_reclaim": PriorMidReclaimStrategy,
    "morning_range_break": MorningRangeBreakStrategy,
    "keltner_am_fade": KeltnerAmFadeStrategy,
    "inside_day_orb": InsideDayOrbStrategy,
    "pivot_bounce": PivotBounceStrategy,
    "vwap_hour_reclaim_fail": VwapHourReclaimFailStrategy,
    "vwap_fh_reclaim": VwapFirstHourStrategy,
    "trend15_pullback5": Trend15Pullback5Strategy,
    "gap_fill_go": GapFillGoStrategy,
    "gap_on_range": GapOnRangeStrategy,
    "open_reject": OpenRejectStrategy,
    "gap_on_confirm": GapOnConfirmStrategy,
    "am_measured": AmMeasuredMoveStrategy,
    "vwap_hold_late": VwapHoldLateStrategy,
    "rvol_open15": RvolOpen15Strategy,
    "vwap_band_fade": VwapBandFadeStrategy,
    "adr_exhaust_fade": AdrExhaustFadeStrategy,
    "pdh_pdl_fail": PdhPdlFailStrategy,
    "morning_reversal": MorningReversalStrategy,
    "vwap_pullback_cont": VwapPullbackContStrategy,
    "ema_stack_pullback": EmaStackPullbackStrategy,
    "ib_mid_fade": IbMidFadeStrategy,
    "three_bar_vwap_fade": ThreeBarVwapFadeStrategy,
    "rsi2_vwap_fade": Rsi2VwapFadeStrategy,
    "vwap_reclaim": VwapReclaimStrategy,
}


def get_strategy(name: str):
    if name == "regime_bot":
        from src.regime.allocator import RegimeAllocatorStrategy
        return RegimeAllocatorStrategy()
    if name not in STRATEGIES:
        raise ValueError(f"Unknown strategy {name!r}; expected one of {list(STRATEGIES) + ['regime_bot']}")
    return STRATEGIES[name]()
