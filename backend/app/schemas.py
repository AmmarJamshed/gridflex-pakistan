"""Pydantic schemas for API I/O."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# Auth
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: str
    email: str
    full_name: str
    role: str
    zone_id: str | None = None
    feeder_id: str | None = None
    organization: str | None = None


# Grid
class ZoneOut(ORMModel):
    id: str
    code: str
    name: str
    city: str
    disco: str
    latitude: float | None = None
    longitude: float | None = None
    peak_threshold_mw: float


class FeederOut(ORMModel):
    id: str
    zone_id: str
    code: str
    name: str
    capacity_mw: float
    current_loading_mw: float


class GridStatusOut(BaseModel):
    current_demand_mw: float
    available_flexibility_mw: float
    peak_demand_mw: float
    renewable_generation_mw: float
    battery_capacity_mwh: float
    active_dr_events: int
    zones: list[dict[str, Any]]
    disclaimer: str = (
        "Illustrative Grid Model — Not an operational representation of "
        "Pakistan's transmission network."
    )


# Flexibility
class FlexibilityBreakdown(BaseModel):
    current_load_kw: float
    essential_load_kw: float
    shiftable_kw: float
    curtailable_kw: float
    storage_kw: float
    generation_kw: float
    available_flexibility_kw: float
    available_energy_kwh: float
    duration_hours: float
    load_factor: float
    peak_demand_kw: float
    baseload_kw: float


class OfferCreate(BaseModel):
    participant_id: str
    flexibility_type: Literal[
        "demand_reduction",
        "demand_shifting",
        "storage_discharge",
        "storage_charge",
        "generation_export",
        "aggregated",
    ]
    power_kw: float = Field(gt=0)
    duration_hours: float = Field(gt=0)
    available_from: datetime
    available_to: datetime
    min_price_pkr_per_kwh: float = Field(gt=0)
    feeder_id: str | None = None
    meter_evidence_ref: str | None = None
    claimed_meter_delta_kwh: float | None = None


class BidCreate(BaseModel):
    zone_id: str
    power_kw: float = Field(gt=0)
    duration_hours: float = Field(gt=0)
    needed_from: datetime
    needed_to: datetime
    max_price_pkr_per_kwh: float = Field(gt=0)
    feeder_id: str | None = None
    urgency: str = "normal"


class OfferOut(ORMModel):
    id: str
    participant_id: str
    seller_user_id: str | None
    zone_id: str
    feeder_id: str | None
    flexibility_type: str
    power_kw: float
    duration_hours: float
    energy_kwh: float
    available_from: datetime
    available_to: datetime
    min_price_pkr_per_kwh: float
    remaining_kw: float
    status: str


class BidOut(ORMModel):
    id: str
    buyer_user_id: str | None
    zone_id: str
    feeder_id: str | None
    power_kw: float
    duration_hours: float
    energy_kwh: float
    needed_from: datetime
    needed_to: datetime
    max_price_pkr_per_kwh: float
    remaining_kw: float
    status: str
    urgency: str


class TransactionOut(ORMModel):
    id: str
    offer_id: str | None
    bid_id: str | None
    seller_user_id: str | None
    buyer_user_id: str | None
    zone_id: str
    feeder_id: str | None
    power_kw: float
    energy_kwh: float
    offer_price: float
    clearing_price: float
    seller_revenue_pkr: float
    buyer_cost_pkr: float
    platform_fee_pkr: float
    grid_fee_pkr: float
    status: str
    verification_status: str
    blockchain_hash: str | None
    created_at: datetime


class ClearMarketRequest(BaseModel):
    zone_id: str | None = None


class ClearMarketResult(BaseModel):
    cleared_volume_kw: float
    cleared_energy_kwh: float
    clearing_price: float | None
    transaction_count: int
    total_seller_revenue_pkr: float
    total_buyer_cost_pkr: float
    total_platform_fee_pkr: float
    total_grid_fee_pkr: float
    transactions: list[TransactionOut]


class WalletOut(ORMModel):
    user_id: str
    flexibility_provided_kwh: float
    demand_reduction_kwh: float
    solar_surplus_kwh: float
    earnings_pkr: float
    pending_settlement_pkr: float


class PricePoint(BaseModel):
    hour: int
    price_pkr_per_kwh: float
    condition: Literal["normal", "peak", "critical"]
    note: str = "Prototype/simulated price — not an official Pakistani tariff."


class LoadShiftRequest(BaseModel):
    appliances: dict[str, float]
    peak_window: tuple[int, int] = (18, 21)
    shift_window: tuple[int, int] = (13, 16)
    shift_appliance: str = "EV"


class LoadShiftResult(BaseModel):
    before_curve: list[float]
    after_curve: list[float]
    before_peak_kw: float
    after_peak_kw: float
    peak_reduction_kw: float
    narrative: str


class ForecastOut(BaseModel):
    forecast_type: str
    horizon: str
    values: list[dict[str, Any]]
    model_name: str


class FraudAlertOut(ORMModel):
    id: str
    participant_id: str | None
    transaction_id: str | None
    alert_type: str
    severity: str
    message: str
    claimed_kwh: float | None
    observed_kwh: float | None
    status: str
    created_at: datetime


class SimulationConfig(BaseModel):
    households: int = 10_000
    commercial: int = 1_000
    industrial: int = 100
    solar_systems: int = 2_000
    batteries: int = 500
    seed: int = 42


class HourlyPoint(BaseModel):
    hour: int
    demand_mw: float
    generation_mw: float
    solar_mw: float
    battery_mw: float
    flexible_demand_mw: float
    cleared_volume_mw: float
    price_pkr: float
    grid_condition: str


class SimulationResult(BaseModel):
    run_id: str
    config: SimulationConfig
    without_gridflex: list[HourlyPoint]
    with_gridflex: list[HourlyPoint]
    peak_without_mw: float
    peak_with_mw: float
    peak_reduction_mw: float
    peak_reduction_pct: float
    energy_shifted_mwh: float
    market_volume_mwh: float
    participant_earnings_pkr: float
    system_savings_pkr: float
    aggregator_earnings_pkr: float
    platform_fee_pkr: float
    utility_value_pkr: float
    story: str


class MarketSummary(BaseModel):
    active_offers: int
    active_bids: int
    cleared_transactions: int
    current_flexibility_price: float
    total_traded_energy_kwh: float
    price_note: str = "Prototype/simulated prices"


class ConfigUpdate(BaseModel):
    platform_fee_pct: float | None = None
    grid_fee_pct: float | None = None
    normal_price_pkr: float | None = None
    peak_price_pkr: float | None = None
    critical_price_pkr: float | None = None


class ParticipantCreate(BaseModel):
    name: str
    category: Literal["residential", "commercial", "industrial", "prosumer", "solar", "battery"]
    zone_code: str
    baseload_kw: float = 1.0
    flexible_kw: float = 0.5
    curtailable_kw: float = 0.3
    solar_kw: float = 0.0
    battery_kwh: float = 0.0


class DREventCreate(BaseModel):
    zone_id: str
    title: str
    starts_at: datetime
    ends_at: datetime
    target_reduction_mw: float


class CongestionTrigger(BaseModel):
    zone_code: str
    loading_factor: float = Field(ge=0.5, le=1.5, default=0.95)