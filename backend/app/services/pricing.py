"""Dynamic pricing engine — prototype/simulated prices only."""

from __future__ import annotations

from app.config import Settings
from app.schemas import PricePoint


def grid_condition(
    demand_mw: float,
    peak_threshold_mw: float,
    flexibility_mw: float,
    congestion_index: float,
) -> str:
    ratio = demand_mw / peak_threshold_mw if peak_threshold_mw > 0 else 0.0
    if ratio >= 0.95 or congestion_index >= 0.9:
        return "critical"
    if ratio >= 0.8 or congestion_index >= 0.7 or flexibility_mw < demand_mw * 0.05:
        return "peak"
    return "normal"


def price_for_condition(condition: str, settings: Settings) -> float:
    mapping = {
        "normal": settings.normal_price_pkr,
        "peak": settings.peak_price_pkr,
        "critical": settings.critical_price_pkr,
    }
    return mapping.get(condition, settings.normal_price_pkr)


def simulate_daily_prices(
    demand_curve: list[float],
    solar_curve: list[float],
    flexibility_curve: list[float],
    peak_threshold_mw: float,
    settings: Settings,
) -> list[PricePoint]:
    points: list[PricePoint] = []
    for hour in range(24):
        demand = demand_curve[hour]
        solar = solar_curve[hour]
        flex = flexibility_curve[hour]
        # Congestion rises with evening peak and falls with midday solar
        congestion = min(1.0, max(0.0, (demand / peak_threshold_mw) - (solar / max(peak_threshold_mw, 1)) * 0.3))
        # Time-of-day urgency
        if hour in (18, 19, 20, 21):
            congestion = min(1.0, congestion + 0.15)
        cond = grid_condition(demand, peak_threshold_mw, flex, congestion)
        price = price_for_condition(cond, settings)
        # Mild renewable depression midday
        if solar > demand * 0.25 and cond == "normal":
            price = max(settings.normal_price_pkr * 0.85, price - 1.0)
        points.append(
            PricePoint(
                hour=hour,
                price_pkr_per_kwh=round(price, 2),
                condition=cond,  # type: ignore[arg-type]
            )
        )
    return points