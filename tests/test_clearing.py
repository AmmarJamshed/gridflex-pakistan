"""Market clearing unit tests."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.services.clearing import clear_example_scenario
from app.services.flexibility import household_example
from app.services.optimization import optimize_load_shift
from app.schemas import LoadShiftRequest


def test_clearing_example_selects_cheapest_compatible():
    result = clear_example_scenario()
    assert result["cleared_volume_kw"] == 400
    assert result["clearing_price"] == 11
    assert result["buyer_cost_pkr"] > result["seller_revenue_pkr"]
    assert abs(sum(s["cleared_kw"] for s in result["selected"]) - 400) < 1e-6


def test_flexibility_example_energy():
    fx = household_example()
    assert fx.available_flexibility_kw == 2.0
    assert fx.available_energy_kwh == 4.0


def test_load_shift_reduces_evening_peak():
    result = optimize_load_shift(
        LoadShiftRequest(
            appliances={"AC": 3, "WaterHeater": 2, "EV": 7, "WashingMachine": 1},
            peak_window=(18, 21),
            shift_window=(13, 16),
            shift_appliance="EV",
        )
    )
    assert result.after_peak_kw < result.before_peak_kw
    assert result.peak_reduction_kw > 0