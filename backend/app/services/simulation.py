"""Pakistan GridFlex 24-hour simulation engine."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.models import HourlyGridSnapshot, SimulationRun
from app.schemas import HourlyPoint, SimulationConfig, SimulationResult
from app.services.pricing import grid_condition, price_for_condition


ZONES = [
    ("KHI", "Karachi", "K-Electric", 24.86, 67.01, 2200),
    ("LHE", "Lahore", "LESCO", 31.52, 74.35, 1800),
    ("ISB", "Islamabad/Rawalpindi", "IESCO", 33.68, 73.05, 900),
    ("PEW", "Peshawar", "PESCO", 34.01, 71.52, 700),
    ("UET", "Quetta", "QESCO", 30.18, 66.99, 400),
    ("MUL", "Multan", "MEPCO", 30.16, 71.52, 1100),
    ("FSD", "Faisalabad", "FESCO", 31.45, 73.13, 1000),
    ("HYD", "Hyderabad", "HESCO", 25.39, 68.36, 650),
]


def _solar_shape(hour: int) -> float:
    if hour < 6 or hour > 18:
        return 0.0
    # Bell curve peaking ~13:00
    return math.exp(-0.5 * ((hour - 13) / 3.2) ** 2)


def _demand_shape(hour: int, category_mix: float = 1.0) -> float:
    # Morning bump, afternoon, strong evening peak (Pakistan-like pattern, stylized)
    morning = 0.75 + 0.25 * math.exp(-0.5 * ((hour - 8) / 1.8) ** 2)
    afternoon = 0.85 + 0.2 * math.exp(-0.5 * ((hour - 14) / 2.5) ** 2)
    evening = 0.9 + 0.55 * math.exp(-0.5 * ((hour - 20) / 2.0) ** 2)
    night = 0.55 + 0.1 * math.cos((hour / 24) * 2 * math.pi)
    return max(morning, afternoon, evening, night) * category_mix


def build_national_curves(cfg: SimulationConfig, rng: np.random.Generator) -> dict[str, np.ndarray]:
    """
    Aggregate MW curves from participant counts without persisting 10k rows.
    Units are MW at system level.
    """
    # Average flexible shares
    res_kw = 1.2
    res_flex = 0.5
    com_kw = 25.0
    com_flex = 8.0
    ind_kw = 800.0
    ind_flex = 250.0
    solar_kw_each = 5.0
    batt_kwh_each = 10.0

    base_demand = np.zeros(24)
    flexible = np.zeros(24)
    solar = np.zeros(24)
    battery = np.zeros(24)

    for h in range(24):
        shape = _demand_shape(h)
        d_res = cfg.households * res_kw * shape / 1000.0
        d_com = cfg.commercial * com_kw * shape / 1000.0
        d_ind = cfg.industrial * ind_kw * (0.7 + 0.3 * shape) / 1000.0
        base_demand[h] = d_res + d_com + d_ind

        evening = 1.35 if 18 <= h <= 21 else 1.0
        f_res = cfg.households * res_flex * (0.5 + 0.7 * shape) * evening / 1000.0
        f_com = cfg.commercial * com_flex * (0.55 + 0.6 * shape) * evening / 1000.0
        f_ind = (
            cfg.industrial
            * ind_flex
            * (0.45 + 0.9 * (1.0 if 14 <= h <= 16 or 18 <= h <= 21 else 0.35))
            / 1000.0
        )
        flexible[h] = f_res + f_com + f_ind

        solar[h] = cfg.solar_systems * solar_kw_each * _solar_shape(h) / 1000.0
        # Battery discharge evening, charge midday
        if 18 <= h <= 21:
            battery[h] = cfg.batteries * batt_kwh_each * 0.15 / 1000.0
        elif 11 <= h <= 15:
            battery[h] = -cfg.batteries * batt_kwh_each * 0.12 / 1000.0
        else:
            battery[h] = 0.0

        # Small noise
        base_demand[h] *= 1 + float(rng.normal(0, 0.01))
        flexible[h] *= 1 + float(rng.normal(0, 0.02))

    generation = solar + np.maximum(battery, 0) + base_demand * 0.15  # stylized other gen share
    return {
        "demand": base_demand,
        "flexible": flexible,
        "solar": solar,
        "battery": battery,
        "generation": generation,
    }


def apply_gridflex(
    curves: dict[str, np.ndarray],
    settings: Settings,
    peak_threshold_mw: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Reduce evening peak via curtailment, solar-aligned shifting, overnight shifting,
    and battery discharge — without creating a higher secondary peak.
    """
    demand = curves["demand"].copy()
    baseline_peak = float(np.max(demand))
    flexible = curves["flexible"]
    battery = curves["battery"].copy()
    cleared = np.zeros(24)

    peak_hours = [18, 19, 20, 21]
    receive_hours = [1, 2, 3, 11, 12, 13, 14, 15]  # night + solar window

    for ph in peak_hours:
        # 40% curtailed (not returned), 45% shifted to off-peak windows
        curtailed = flexible[ph] * 0.40
        movable = flexible[ph] * 0.45
        demand[ph] -= curtailed + movable
        cleared[ph] += curtailed + movable
        share = movable / len(receive_hours)
        for rh in receive_hours:
            demand[rh] += share

    for ph in peak_hours:
        if battery[ph] > 0:
            demand[ph] -= battery[ph] * 0.95
            cleared[ph] += battery[ph] * 0.6

    # Keep system peak strictly below baseline (clip any secondary bulge)
    for h in range(24):
        if h not in peak_hours and demand[h] > baseline_peak * 0.92:
            overflow = demand[h] - baseline_peak * 0.88
            demand[h] -= overflow
            # push residual further into deepest night valley
            demand[3] += overflow * 0.5

    prices = np.zeros(24)
    for h in range(24):
        cong = min(1.0, demand[h] / peak_threshold_mw)
        cond = grid_condition(float(demand[h]), peak_threshold_mw, float(flexible[h]), cong)
        prices[h] = price_for_condition(cond, settings)

    return demand, cleared, prices, flexible


def run_pakistan_simulation(
    db: Session,
    cfg: SimulationConfig | None = None,
    settings: Settings | None = None,
) -> SimulationResult:
    settings = settings or get_settings()
    cfg = cfg or SimulationConfig(
        households=settings.sim_households,
        commercial=settings.sim_commercial,
        industrial=settings.sim_industrial,
        solar_systems=settings.sim_solar,
        batteries=settings.sim_batteries,
    )
    rng = np.random.default_rng(cfg.seed)
    curves = build_national_curves(cfg, rng)
    peak_threshold = float(np.max(curves["demand"]) * 0.92)

    without_points: list[HourlyPoint] = []
    for h in range(24):
        d = float(curves["demand"][h])
        cong = min(1.0, d / peak_threshold)
        cond = grid_condition(d, peak_threshold, float(curves["flexible"][h]), cong)
        price = price_for_condition(cond, settings)
        without_points.append(
            HourlyPoint(
                hour=h,
                demand_mw=round(d, 2),
                generation_mw=round(float(curves["generation"][h]), 2),
                solar_mw=round(float(curves["solar"][h]), 2),
                battery_mw=round(float(curves["battery"][h]), 2),
                flexible_demand_mw=round(float(curves["flexible"][h]), 2),
                cleared_volume_mw=0.0,
                price_pkr=round(price, 2),
                grid_condition=cond,
            )
        )

    demand_w, cleared, prices, flex = apply_gridflex(curves, settings, peak_threshold)
    with_points: list[HourlyPoint] = []
    for h in range(24):
        d = float(demand_w[h])
        cong = min(1.0, d / peak_threshold)
        cond = grid_condition(d, peak_threshold, float(flex[h]), cong)
        with_points.append(
            HourlyPoint(
                hour=h,
                demand_mw=round(d, 2),
                generation_mw=round(float(curves["generation"][h] + max(0, curves["battery"][h])), 2),
                solar_mw=round(float(curves["solar"][h]), 2),
                battery_mw=round(float(curves["battery"][h]), 2),
                flexible_demand_mw=round(float(flex[h]), 2),
                cleared_volume_mw=round(float(cleared[h]), 2),
                price_pkr=round(float(prices[h]), 2),
                grid_condition=cond,
            )
        )

    peak_without = max(p.demand_mw for p in without_points)
    peak_with = max(p.demand_mw for p in with_points)
    peak_reduction = peak_without - peak_with
    peak_pct = (peak_reduction / peak_without * 100) if peak_without else 0.0
    energy_shifted = float(np.sum(cleared))
    market_volume = energy_shifted  # MWh if each point is MW for 1 hour
    avg_price = float(np.mean(prices))
    gross = market_volume * 1000 * avg_price  # MW*h * 1000 = kWh
    platform_fee = gross * settings.platform_fee_pct
    grid_fee = gross * settings.grid_fee_pct
    participant_earnings = gross - platform_fee - grid_fee
    # Aggregator takes ~15% of participant pool in demo narrative
    aggregator_earnings = participant_earnings * 0.15
    consumer_earnings = participant_earnings - aggregator_earnings
    # System savings: avoided peaker / shed cost assumption PKR 30/kWh on peak reduction energy
    peak_hours_energy = peak_reduction * 4  # 4 peak hours
    system_savings = peak_hours_energy * 1000 * 30

    results_payload: dict[str, Any] = {
        "peak_without_mw": peak_without,
        "peak_with_mw": peak_with,
        "peak_reduction_mw": peak_reduction,
        "peak_reduction_pct": peak_pct,
        "energy_shifted_mwh": energy_shifted,
        "market_volume_mwh": market_volume,
    }

    run = SimulationRun(
        name="RUN PAKISTAN GRIDFLEX SIMULATION",
        config=cfg.model_dump(),
        results=results_payload,
    )
    db.add(run)
    db.flush()

    for scenario, points in (("without_gridflex", without_points), ("with_gridflex", with_points)):
        for p in points:
            db.add(
                HourlyGridSnapshot(
                    simulation_run_id=run.id,
                    zone_id=None,
                    hour=p.hour,
                    demand_mw=p.demand_mw,
                    generation_mw=p.generation_mw,
                    solar_mw=p.solar_mw,
                    battery_mw=p.battery_mw,
                    flexible_demand_mw=p.flexible_demand_mw,
                    cleared_volume_mw=p.cleared_volume_mw,
                    price_pkr=p.price_pkr,
                    grid_condition=p.grid_condition,
                    scenario=scenario,
                )
            )
    db.commit()

    story = (
        "Pakistan has electricity demand concentrated at certain times. "
        "Instead of simply building more generation capacity, GRIDFLEX identifies "
        "consumption that can be shifted, reduced, stored or coordinated. "
        f"In this run, {cfg.households:,} households, {cfg.commercial:,} commercial and "
        f"{cfg.industrial:,} industrial users plus {cfg.solar_systems:,} solar and "
        f"{cfg.batteries:,} battery systems form an aggregated flexibility resource. "
        f"Peak demand falls from {peak_without:.1f} MW to {peak_with:.1f} MW "
        f"({peak_pct:.1f}% reduction). Physical power still flows on the grid; "
        "the marketplace settles verified flexibility financially."
    )

    return SimulationResult(
        run_id=run.id,
        config=cfg,
        without_gridflex=without_points,
        with_gridflex=with_points,
        peak_without_mw=round(peak_without, 2),
        peak_with_mw=round(peak_with, 2),
        peak_reduction_mw=round(peak_reduction, 2),
        peak_reduction_pct=round(peak_pct, 2),
        energy_shifted_mwh=round(energy_shifted, 2),
        market_volume_mwh=round(market_volume, 2),
        participant_earnings_pkr=round(consumer_earnings, 2),
        system_savings_pkr=round(system_savings, 2),
        aggregator_earnings_pkr=round(aggregator_earnings, 2),
        platform_fee_pkr=round(platform_fee, 2),
        utility_value_pkr=round(grid_fee + system_savings * 0.1, 2),
        story=story,
    )