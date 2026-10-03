"""ORM models for GRIDFLEX Pakistan (SQLite-friendly string enums)."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class GridZone(Base):
    __tablename__ = "grid_zones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(128))
    city: Mapped[str] = mapped_column(String(64))
    disco: Mapped[str] = mapped_column(String(64))
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_threshold_mw: Mapped[float] = mapped_column(Float, default=500.0)

    feeders: Mapped[list[Feeder]] = relationship(back_populates="zone")
    participants: Mapped[list[Participant]] = relationship(back_populates="zone")


class Feeder(Base):
    __tablename__ = "feeders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    zone_id: Mapped[str] = mapped_column(ForeignKey("grid_zones.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    capacity_mw: Mapped[float] = mapped_column(Float)
    current_loading_mw: Mapped[float] = mapped_column(Float, default=0.0)

    zone: Mapped[GridZone] = relationship(back_populates="feeders")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(64), index=True)
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("grid_zones.id"), nullable=True)
    feeder_id: Mapped[str | None] = mapped_column(ForeignKey("feeders.id"), nullable=True)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    wallet: Mapped[Wallet | None] = relationship(back_populates="user", uselist=False)


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    external_ref: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    name: Mapped[str] = mapped_column(String(255))
    zone_id: Mapped[str] = mapped_column(ForeignKey("grid_zones.id"), index=True)
    feeder_id: Mapped[str | None] = mapped_column(ForeignKey("feeders.id"), nullable=True)
    baseload_kw: Mapped[float] = mapped_column(Float, default=0.0)
    flexible_kw: Mapped[float] = mapped_column(Float, default=0.0)
    curtailable_kw: Mapped[float] = mapped_column(Float, default=0.0)
    solar_kw: Mapped[float] = mapped_column(Float, default=0.0)
    battery_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    battery_soc: Mapped[float] = mapped_column(Float, default=0.5)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    zone: Mapped[GridZone] = relationship(back_populates="participants")
    meters: Mapped[list[Meter]] = relationship(back_populates="participant")


class Meter(Base):
    __tablename__ = "meters"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    participant_id: Mapped[str] = mapped_column(ForeignKey("participants.id"), index=True)
    meter_serial: Mapped[str] = mapped_column(String(64), unique=True)
    is_simulated: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="online")

    participant: Mapped[Participant] = relationship(back_populates="meters")
    readings: Mapped[list[MeterReading]] = relationship(back_populates="meter")


class MeterReading(Base):
    __tablename__ = "meter_readings"
    __table_args__ = (UniqueConstraint("meter_id", "ts", name="uq_meter_ts"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meter_id: Mapped[str] = mapped_column(ForeignKey("meters.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, index=True)
    voltage_v: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_a: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_kw: Mapped[float] = mapped_column(Float)
    energy_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    power_factor: Mapped[float | None] = mapped_column(Float, nullable=True)
    frequency_hz: Mapped[float | None] = mapped_column(Float, nullable=True)
    solar_kw: Mapped[float] = mapped_column(Float, default=0.0)
    battery_soc: Mapped[float | None] = mapped_column(Float, nullable=True)

    meter: Mapped[Meter] = relationship(back_populates="readings")


class FlexibilityOffer(Base):
    __tablename__ = "flexibility_offers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    participant_id: Mapped[str] = mapped_column(ForeignKey("participants.id"), index=True)
    seller_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("grid_zones.id"), index=True)
    feeder_id: Mapped[str | None] = mapped_column(ForeignKey("feeders.id"), nullable=True)
    flexibility_type: Mapped[str] = mapped_column(String(64))
    power_kw: Mapped[float] = mapped_column(Float)
    duration_hours: Mapped[float] = mapped_column(Float)
    energy_kwh: Mapped[float] = mapped_column(Float)
    available_from: Mapped[datetime] = mapped_column(DateTime)
    available_to: Mapped[datetime] = mapped_column(DateTime)
    min_price_pkr_per_kwh: Mapped[float] = mapped_column(Float)
    remaining_kw: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="open")
    meter_evidence_ref: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FlexibilityBid(Base):
    __tablename__ = "flexibility_bids"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    buyer_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("grid_zones.id"), index=True)
    feeder_id: Mapped[str | None] = mapped_column(ForeignKey("feeders.id"), nullable=True)
    power_kw: Mapped[float] = mapped_column(Float)
    duration_hours: Mapped[float] = mapped_column(Float)
    energy_kwh: Mapped[float] = mapped_column(Float)
    needed_from: Mapped[datetime] = mapped_column(DateTime)
    needed_to: Mapped[datetime] = mapped_column(DateTime)
    max_price_pkr_per_kwh: Mapped[float] = mapped_column(Float)
    remaining_kw: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="open")
    urgency: Mapped[str] = mapped_column(String(32), default="normal")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class MarketTransaction(Base):
    __tablename__ = "market_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    offer_id: Mapped[str | None] = mapped_column(ForeignKey("flexibility_offers.id"), nullable=True)
    bid_id: Mapped[str | None] = mapped_column(ForeignKey("flexibility_bids.id"), nullable=True)
    seller_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    buyer_user_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    zone_id: Mapped[str] = mapped_column(ForeignKey("grid_zones.id"), index=True)
    feeder_id: Mapped[str | None] = mapped_column(ForeignKey("feeders.id"), nullable=True)
    power_kw: Mapped[float] = mapped_column(Float)
    energy_kwh: Mapped[float] = mapped_column(Float)
    offer_price: Mapped[float] = mapped_column(Float)
    clearing_price: Mapped[float] = mapped_column(Float)
    seller_revenue_pkr: Mapped[float] = mapped_column(Float)
    buyer_cost_pkr: Mapped[float] = mapped_column(Float)
    platform_fee_pkr: Mapped[float] = mapped_column(Float)
    grid_fee_pkr: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(32), default="cleared")
    meter_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="pending")
    blockchain_hash: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Wallet(Base):
    __tablename__ = "wallets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    flexibility_provided_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    demand_reduction_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    solar_surplus_kwh: Mapped[float] = mapped_column(Float, default=0.0)
    earnings_pkr: Mapped[float] = mapped_column(Float, default=0.0)
    pending_settlement_pkr: Mapped[float] = mapped_column(Float, default=0.0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="wallet")


class Settlement(Base):
    __tablename__ = "settlements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("market_transactions.id"))
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    amount_pkr: Mapped[float] = mapped_column(Float)
    fee_pkr: Mapped[float] = mapped_column(Float, default=0.0)
    direction: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DemandResponseEvent(Base):
    __tablename__ = "demand_response_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    zone_id: Mapped[str] = mapped_column(ForeignKey("grid_zones.id"))
    title: Mapped[str] = mapped_column(String(255))
    starts_at: Mapped[datetime] = mapped_column(DateTime)
    ends_at: Mapped[datetime] = mapped_column(DateTime)
    target_reduction_mw: Mapped[float] = mapped_column(Float)
    achieved_reduction_mw: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(32), default="scheduled")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class FraudAlert(Base):
    __tablename__ = "fraud_alerts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    participant_id: Mapped[str | None] = mapped_column(ForeignKey("participants.id"), nullable=True)
    transaction_id: Mapped[str | None] = mapped_column(
        ForeignKey("market_transactions.id"), nullable=True
    )
    alert_type: Mapped[str] = mapped_column(String(64))
    severity: Mapped[str] = mapped_column(String(32), default="medium")
    message: Mapped[str] = mapped_column(Text)
    claimed_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    observed_kwh: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    config: Mapped[dict] = mapped_column(JSON)
    results: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HourlyGridSnapshot(Base):
    __tablename__ = "hourly_grid_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    simulation_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("simulation_runs.id"), nullable=True, index=True
    )
    zone_id: Mapped[str | None] = mapped_column(ForeignKey("grid_zones.id"), nullable=True)
    hour: Mapped[int] = mapped_column(Integer)
    demand_mw: Mapped[float] = mapped_column(Float)
    generation_mw: Mapped[float] = mapped_column(Float)
    solar_mw: Mapped[float] = mapped_column(Float)
    battery_mw: Mapped[float] = mapped_column(Float)
    flexible_demand_mw: Mapped[float] = mapped_column(Float)
    cleared_volume_mw: Mapped[float] = mapped_column(Float, default=0.0)
    price_pkr: Mapped[float | None] = mapped_column(Float, nullable=True)
    grid_condition: Mapped[str] = mapped_column(String(32), default="normal")
    scenario: Mapped[str] = mapped_column(String(32))


class PlatformConfig(Base):
    __tablename__ = "platform_config"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict | float | str] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)