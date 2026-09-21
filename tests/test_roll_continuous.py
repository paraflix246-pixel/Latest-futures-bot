"""Front-month roll stitches two contracts and ratio-adjusts older bars."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.data.roll_continuous import backward_ratio_adjust, pick_front_month, to_loader_csv


def test_volume_roll_and_backward_adjust():
    idx_a = pd.date_range("2024-03-01", periods=3, freq="1D", tz="UTC")
    idx_b = pd.date_range("2024-03-01", periods=3, freq="1D", tz="UTC")
    a = pd.DataFrame(
        {
            "datetime": idx_a,
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, 101.0, 101.0],
            "low": [99.0, 99.0, 99.0],
            "close": [100.0, 100.0, 100.0],
            "volume": [10.0, 10.0, 1.0],
        }
    )
    b = pd.DataFrame(
        {
            "datetime": idx_b,
            "open": [200.0, 200.0, 200.0],
            "high": [201.0, 201.0, 201.0],
            "low": [199.0, 199.0, 199.0],
            "close": [200.0, 200.0, 200.0],
            "volume": [1.0, 1.0, 50.0],
        }
    )
    contracts = [
        {"ticker": "MNQH4", "last_trade_date": "2024-03-20"},
        {"ticker": "MNQM4", "last_trade_date": "2024-06-20"},
    ]
    raw, rolls = pick_front_month({"MNQH4": a, "MNQM4": b}, contracts, min_days_to_expiry=5)
    assert len(raw) == 3
    assert raw["ticker"].iloc[0] == "MNQH4"
    assert raw["ticker"].iloc[-1] == "MNQM4"
    assert len(rolls) == 1
    adj = backward_ratio_adjust(raw, rolls)
    # Latest segment stays at 200; older 100s are scaled by 200/100 = 2.
    assert abs(adj["close"].iloc[-1] - 200.0) < 1e-9
    assert abs(adj["close"].iloc[0] - 200.0) < 1e-6
    csv = to_loader_csv(adj)
    assert list(csv.columns) == ["datetime", "open", "high", "low", "close", "volume"]


def test_roll_infers_hmuz_expiry_when_metadata_missing():
    idx_a = pd.date_range("2024-03-01", periods=3, freq="1D", tz="UTC")
    idx_b = pd.date_range("2024-03-01", periods=3, freq="1D", tz="UTC")
    a = pd.DataFrame(
        {
            "datetime": idx_a,
            "open": [100.0, 100.0, 100.0],
            "high": [101.0, 101.0, 101.0],
            "low": [99.0, 99.0, 99.0],
            "close": [100.0, 100.0, 100.0],
            "volume": [10.0, 10.0, 1.0],
        }
    )
    b = pd.DataFrame(
        {
            "datetime": idx_b,
            "open": [200.0, 200.0, 200.0],
            "high": [201.0, 201.0, 201.0],
            "low": [199.0, 199.0, 199.0],
            "close": [200.0, 200.0, 200.0],
            "volume": [1.0, 1.0, 50.0],
        }
    )
    raw, rolls = pick_front_month(
        {"MNQH4": a, "MNQM4": b},
        [{"ticker": "MNQH4"}, {"ticker": "MNQM4"}],
        min_days_to_expiry=5,
    )
    assert len(raw) == 3
    assert len(rolls) == 1
