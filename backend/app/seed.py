"""Seed illustrative Pakistan zones, demo users, sample participants & market data."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.auth import hash_password
from app.config import get_settings
from app.models import (
    DemandResponseEvent,
    Feeder,
    FlexibilityBid,
    FlexibilityOffer,
    GridZone,
    Meter,
    MeterReading,
    Participant,
    PlatformConfig,
    User,
    Wallet,
)
from app.services.simulation import ZONES


def seed_if_empty(db: Session) -> None:
    if db.query(GridZone).first():
        return

    settings = get_settings()
    zones: dict[str, GridZone] = {}
    feeders: dict[str, Feeder] = {}

    for code, city, disco, lat, lon, peak in ZONES:
        z = GridZone(
            code=code,
            name=f"{city} Zone",
            city=city,
            disco=disco,
            latitude=lat,
            longitude=lon,
            peak_threshold_mw=float(peak),
        )
        db.add(z)
        db.flush()
        zones[code] = z
        for i in range(1, 3):
            f = Feeder(
                zone_id=z.id,
                code=f"FEEDER-{code}-{i:03d}",
                name=f"{city} Feeder {i}",
                capacity_mw=peak / 8,
                current_loading_mw=peak / 8 * (0.55 + 0.1 * i),
            )
            db.add(f)
            db.flush()
            feeders[f.code] = f

    demo_users = [
        ("consumer@gridflex.pk", "Ayesha Khan", "residential", "KHI", "FEEDER-KHI-001", "Household"),
        ("commercial@gridflex.pk", "Lahore Mall Ops", "commercial", "LHE", "FEEDER-LHE-001", "Commercial"),
        ("prosumer@gridflex.pk", "Hassan Solar Home", "prosumer", "ISB", "FEEDER-ISB-001", "Prosumer"),
        ("aggregator@gridflex.pk", "FlexAgg Pakistan", "aggregator", "LHE", "FEEDER-LHE-002", "FlexAgg PK"),
        ("utility@gridflex.pk", "DISCO Operator", "utility", "KHI", "FEEDER-KHI-002", "Utility Desk"),
        ("admin@gridflex.pk", "GRIDFLEX Admin", "admin", "ISB", None, "GRIDFLEX"),
    ]

    user_map: dict[str, User] = {}
    for email, name, role, zcode, fcode, org in demo_users:
        u = User(
            email=email,
            password_hash=hash_password("demo1234"),
            full_name=name,
            role=role,
            zone_id=zones[zcode].id,
            feeder_id=feeders[fcode].id if fcode else None,
            organization=org,
        )
        db.add(u)
        db.flush()
        db.add(Wallet(user_id=u.id, earnings_pkr=1350 if role == "residential" else 0))
        user_map[email] = u

    # Sample participants
    samples = [
        ("RES-KHI-001", "residential", "Karachi Home A", "KHI", "FEEDER-KHI-001", 3.0, 1.5, 1.0, 0, 0),
        ("COM-LHE-001", "commercial", "Lahore Office Park", "LHE", "FEEDER-LHE-001", 40, 15, 10, 50, 0),
        ("IND-FSD-001", "industrial", "Faisalabad Factory", "FSD", "FEEDER-FSD-001", 700, 200, 100, 0, 0),
        ("PRO-ISB-001", "prosumer", "Islamabad Prosumer", "ISB", "FEEDER-ISB-001", 5, 2, 1, 8, 10),
        ("SOL-MUL-001", "solar", "Multan Rooftop Fleet", "MUL", "FEEDER-MUL-001", 2, 0.5, 0.2, 20, 0),
        ("BAT-PEW-001", "battery", "Peshawar Community Battery", "PEW", "FEEDER-PEW-001", 1, 0, 0, 0, 50),
    ]
    now = datetime.utcnow()
    participants: list[Participant] = []
    for ref, cat, name, zc, fc, base, flex, curt, solar, batt in samples:
        p = Participant(
            user_id=user_map["consumer@gridflex.pk"].id if cat == "residential" else None,
            external_ref=ref,
            category=cat,
            name=name,
            zone_id=zones[zc].id,
            feeder_id=feeders[fc].id,
            baseload_kw=base,
            flexible_kw=flex,
            curtailable_kw=curt,
            solar_kw=solar,
            battery_kwh=batt,
            battery_soc=0.65,
        )
        if cat == "prosumer":
            p.user_id = user_map["prosumer@gridflex.pk"].id
        if cat == "commercial":
            p.user_id = user_map["commercial@gridflex.pk"].id
        db.add(p)
        db.flush()
        participants.append(p)
        meter = Meter(
            participant_id=p.id,
            meter_serial=f"SIM-{ref}",
            is_simulated=True,
            last_seen_at=now,
            status="online",
        )
        db.add(meter)
        db.flush()
        for h in range(24):
            load = base + flex * (0.5 + 0.5 * ((h % 12) / 12)) + curt * (0.3 if 18 <= h <= 21 else 0.1)
            sol = solar * max(0, 1 - abs(h - 13) / 7)
            db.add(
                MeterReading(
                    meter_id=meter.id,
                    ts=now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(hours=h),
                    voltage_v=230 + (h % 3),
                    current_a=load * 1000 / 230,
                    power_kw=round(load, 3),
                    energy_kwh=round(load, 3),
                    power_factor=0.92,
                    frequency_hz=50.0,
                    solar_kw=round(sol, 3),
                    battery_soc=0.65,
                )
            )

    # Link residential participant to consumer user
    participants[0].user_id = user_map["consumer@gridflex.pk"].id

    # Seed marketplace offers/bids (same zone matches)
    khi = zones["KHI"]
    offer = FlexibilityOffer(
        participant_id=participants[0].id,
        seller_user_id=user_map["consumer@gridflex.pk"].id,
        zone_id=khi.id,
        feeder_id=feeders["FEEDER-KHI-001"].id,
        flexibility_type="demand_reduction",
        power_kw=500,
        duration_hours=2,
        energy_kwh=1000,
        available_from=now.replace(hour=14, minute=0, second=0, microsecond=0),
        available_to=now.replace(hour=16, minute=0, second=0, microsecond=0),
        min_price_pkr_per_kwh=8,
        remaining_kw=500,
        status="open",
        meter_evidence_ref="SIM-RES-KHI-001",
    )
    # Scale down demo offer to realistic household + keep a large aggregator-style offer
    offer.power_kw = 2.5
    offer.energy_kwh = 5.0
    offer.remaining_kw = 2.5

    agg_offer = FlexibilityOffer(
        participant_id=participants[1].id,
        seller_user_id=user_map["aggregator@gridflex.pk"].id,
        zone_id=khi.id,
        feeder_id=feeders["FEEDER-KHI-001"].id,
        flexibility_type="aggregated",
        power_kw=500,
        duration_hours=2,
        energy_kwh=1000,
        available_from=now.replace(hour=14, minute=0, second=0, microsecond=0),
        available_to=now.replace(hour=16, minute=0, second=0, microsecond=0),
        min_price_pkr_per_kwh=8,
        remaining_kw=500,
        status="open",
        meter_evidence_ref="AGG-KHI-POOL",
    )
    bid = FlexibilityBid(
        buyer_user_id=user_map["utility@gridflex.pk"].id,
        zone_id=khi.id,
        feeder_id=feeders["FEEDER-KHI-001"].id,
        power_kw=300,
        duration_hours=2,
        energy_kwh=600,
        needed_from=now.replace(hour=14, minute=0, second=0, microsecond=0),
        needed_to=now.replace(hour=16, minute=0, second=0, microsecond=0),
        max_price_pkr_per_kwh=12,
        remaining_kw=300,
        status="open",
        urgency="peak",
    )
    # Cross-zone bid that should NOT match Karachi offers
    lhe_bid = FlexibilityBid(
        buyer_user_id=user_map["utility@gridflex.pk"].id,
        zone_id=zones["LHE"].id,
        feeder_id=feeders["FEEDER-LHE-001"].id,
        power_kw=200,
        duration_hours=2,
        energy_kwh=400,
        needed_from=now.replace(hour=14, minute=0, second=0, microsecond=0),
        needed_to=now.replace(hour=16, minute=0, second=0, microsecond=0),
        max_price_pkr_per_kwh=12,
        remaining_kw=200,
        status="open",
        urgency="normal",
    )
    db.add_all([offer, agg_offer, bid, lhe_bid])

    db.add(
        DemandResponseEvent(
            zone_id=khi.id,
            title="Karachi Evening Peak DR",
            starts_at=now.replace(hour=18, minute=0, second=0, microsecond=0),
            ends_at=now.replace(hour=21, minute=0, second=0, microsecond=0),
            target_reduction_mw=120,
            achieved_reduction_mw=45,
            status="active",
        )
    )

    for key, value in [
        ("platform_fee_pct", settings.platform_fee_pct),
        ("grid_fee_pct", settings.grid_fee_pct),
        ("normal_price_pkr", settings.normal_price_pkr),
        ("peak_price_pkr", settings.peak_price_pkr),
        ("critical_price_pkr", settings.critical_price_pkr),
    ]:
        db.add(PlatformConfig(key=key, value=value))

    db.commit()