"""Flexibility classification engine — not generation minus consumption."""

from __future__ import annotations

from dataclasses import dataclass

from app.models import Participant
from app.schemas import FlexibilityBreakdown


@dataclass
class LoadComponents:
    baseload_kw: float
    shiftable_kw: float
    curtailable_kw: float
    storage_discharge_kw: float
    generation_kw: float


def classify_participant(p: Participant, duration_hours: float = 2.0) -> FlexibilityBreakdown:
    """
    Classify electricity usage into base / shiftable / curtailable / storage / generation.

    Available flexibility = shiftable + curtailable + dispatchable storage discharge.
    Generation surplus is tracked separately for marketplace export offers.
    """
    baseload = max(0.0, p.baseload_kw)
    shiftable = max(0.0, p.flexible_kw)
    curtailable = max(0.0, p.curtailable_kw)
    generation = max(0.0, p.solar_kw)
    # Battery: assume up to 25% of energy capacity can be discharged per hour for 2h window
    storage_kw = 0.0
    if p.battery_kwh > 0:
        usable_fraction = min(1.0, max(0.0, p.battery_soc))
        storage_kw = (p.battery_kwh * usable_fraction * 0.5) / max(duration_hours, 0.25)

    current_load = baseload + shiftable + curtailable
    essential = baseload
    available_flex_kw = shiftable + curtailable + storage_kw
    available_energy = available_flex_kw * duration_hours

    peak = current_load * 1.15
    avg = current_load * 0.7
    load_factor = avg / peak if peak > 0 else 0.0

    return FlexibilityBreakdown(
        current_load_kw=round(current_load, 3),
        essential_load_kw=round(essential, 3),
        shiftable_kw=round(shiftable, 3),
        curtailable_kw=round(curtailable, 3),
        storage_kw=round(storage_kw, 3),
        generation_kw=round(generation, 3),
        available_flexibility_kw=round(available_flex_kw, 3),
        available_energy_kwh=round(available_energy, 3),
        duration_hours=duration_hours,
        load_factor=round(load_factor, 3),
        peak_demand_kw=round(peak, 3),
        baseload_kw=round(baseload, 3),
    )


def household_example() -> FlexibilityBreakdown:
    """Documented example: 5 kW load, 3 kW essential → 2 kW flexibility × 2 h = 4 kWh."""
    return FlexibilityBreakdown(
        current_load_kw=5.0,
        essential_load_kw=3.0,
        shiftable_kw=1.2,
        curtailable_kw=0.8,
        storage_kw=0.0,
        generation_kw=0.0,
        available_flexibility_kw=2.0,
        available_energy_kwh=4.0,
        duration_hours=2.0,
        load_factor=0.7,
        peak_demand_kw=5.75,
        baseload_kw=3.0,
    )