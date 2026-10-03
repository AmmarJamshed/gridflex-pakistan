"""REST API routes for GRIDFLEX Pakistan."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    get_optional_user,
)
from app.config import Settings, get_settings
from app.database import get_db
from app.models import (
    DemandResponseEvent,
    Feeder,
    FlexibilityBid,
    FlexibilityOffer,
    FraudAlert,
    GridZone,
    MarketTransaction,
    Meter,
    Participant,
    PlatformConfig,
    SimulationRun,
    User,
    Wallet,
)
from app.schemas import (
    BidCreate,
    BidOut,
    ClearMarketRequest,
    ClearMarketResult,
    ConfigUpdate,
    CongestionTrigger,
    DREventCreate,
    FlexibilityBreakdown,
    ForecastOut,
    FraudAlertOut,
    GridStatusOut,
    LoadShiftRequest,
    LoadShiftResult,
    LoginRequest,
    MarketSummary,
    OfferCreate,
    OfferOut,
    ParticipantCreate,
    PricePoint,
    SimulationConfig,
    SimulationResult,
    Token,
    TransactionOut,
    UserOut,
    WalletOut,
    ZoneOut,
)
from app.services.clearing import clear_example_scenario, clear_zone
from app.services.flexibility import classify_participant, household_example
from app.services.forecasting import forecast_all, isolation_forest_scores
from app.services.fraud import verify_flexibility_claim
from app.services.optimization import optimize_load_shift
from app.services.pricing import simulate_daily_prices
from app.services.settlement import get_or_create_wallet
from app.services.simulation import run_pakistan_simulation

router = APIRouter()


# ----- Auth -----
@router.post("/auth/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: Annotated[Session, Depends(get_db)],
) -> Token:
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    return Token(access_token=create_access_token(user.id, user.role))


@router.post("/auth/token", response_model=Token)
def login_json(body: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> Token:
    user = authenticate_user(db, body.email, body.password)
    if not user:
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    return Token(access_token=create_access_token(user.id, user.role))


@router.get("/auth/me", response_model=UserOut)
def me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


# ----- Concept / education -----
@router.get("/concept/flexibility-accounting")
def flexibility_accounting_layer() -> dict[str, Any]:
    return {
        "title": "Flexibility Accounting Layer",
        "subtitle": "Virtual electricity ≠ peer-to-peer physical transfer",
        "steps": [
            "Meter measures actual electricity at the premise.",
            "Consumer changes consumption, storage, or generation behavior.",
            "System verifies the change against meter evidence.",
            "Marketplace calculates flexibility provided (kW / kWh).",
            "Matching engine allocates economic value within grid constraints.",
            "Settlement occurs financially (flexibility wallet / PKR credits).",
            "Physical electricity remains governed by the electrical grid / DISCO network.",
        ],
        "distinctions": [
            "Physical electricity flow",
            "Grid capacity",
            "Demand reduction",
            "Demand shifting",
            "Distributed generation",
            "Battery storage",
            "Net metering / net billing",
            "Demand response",
            "Virtual electricity / flexibility credits",
            "Financial settlement",
        ],
    }


@router.get("/concept/regulatory")
def regulatory_compatibility() -> dict[str, Any]:
    return {
        "disclaimer": (
            "Research/prototype platform. Does not represent a legally authorized "
            "electricity market. Do not invent or assume P2P trading is currently permitted."
        ),
        "current_regulatory_facts": [
            "NEPRA is Pakistan's electricity regulator for tariffs, licensing, and market frameworks.",
            "NTDC operates the national transmission system; DISCOs handle distribution.",
            "CPPA-G plays a central role in power purchase / market administration.",
            "Net metering / net billing frameworks exist for eligible distributed solar under applicable NEPRA rules — separate from a flexibility marketplace.",
            "Consumer electricity tariffs are regulated; this app's PKR/kWh figures are simulated prototypes, not official tariffs.",
            "Peer-to-peer electricity trading between arbitrary consumers is not assumed to be currently authorized.",
        ],
        "areas_requiring_approval_or_review": [
            "NEPRA market rules for demand response and flexibility products",
            "NTDC / system operator coordination for aggregated DR",
            "DISCO distribution licensing and operational procedures",
            "CPPA-G / wholesale market interface design",
            "Smart metering data access and settlement-grade metrology",
            "Tariff and incentive design for flexibility compensation",
            "Data privacy and consumer protection",
            "Aggregator registration / licensing models",
        ],
        "proposed_future_model": [
            "Zone/feeder-constrained flexibility markets settled financially",
            "Aggregators as virtual power resources under regulated participation",
            "Verified meter-based flexibility accounting layered on physical grid operations",
            "Optional future blockchain audit hashes — not required for operation",
        ],
        "institutions": ["NEPRA", "NTDC", "DISCOs", "CPPA-G"],
    }


# ----- Grid -----
@router.get("/grid/zones", response_model=list[ZoneOut])
def list_zones(db: Annotated[Session, Depends(get_db)]) -> list[GridZone]:
    return db.query(GridZone).all()


@router.get("/grid/status", response_model=GridStatusOut)
def grid_status(db: Annotated[Session, Depends(get_db)]) -> GridStatusOut:
    zones = db.query(GridZone).all()
    feeders = db.query(Feeder).all()
    participants = db.query(Participant).all()
    dr = db.query(DemandResponseEvent).filter(DemandResponseEvent.status == "active").count()

    demand = sum(f.current_loading_mw for f in feeders) * 3.5  # scale illustrative
    flex = sum(p.flexible_kw + p.curtailable_kw for p in participants) / 1000.0 + 850
    renew = sum(p.solar_kw for p in participants) / 1000.0 + 420
    batt = sum(p.battery_kwh for p in participants) / 1000.0 + 35
    peak = max((z.peak_threshold_mw for z in zones), default=1000) * 0.9

    zone_payload = []
    for z in zones:
        zf = [f for f in feeders if f.zone_id == z.id]
        loading = sum(f.current_loading_mw for f in zf)
        ratio = loading / z.peak_threshold_mw if z.peak_threshold_mw else 0
        cond = "critical" if ratio > 0.25 else "peak" if ratio > 0.18 else "normal"
        zone_payload.append(
            {
                "code": z.code,
                "name": z.name,
                "city": z.city,
                "disco": z.disco,
                "demand_mw": round(loading * 4.2, 1),
                "flexibility_mw": round(z.peak_threshold_mw * 0.08, 1),
                "congestion": cond,
                "latitude": z.latitude,
                "longitude": z.longitude,
            }
        )

    return GridStatusOut(
        current_demand_mw=round(demand, 1),
        available_flexibility_mw=round(flex, 1),
        peak_demand_mw=round(peak, 1),
        renewable_generation_mw=round(renew, 1),
        battery_capacity_mwh=round(batt, 1),
        active_dr_events=dr,
        zones=zone_payload,
    )


@router.post("/grid/trigger-congestion")
def trigger_congestion(
    body: CongestionTrigger,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    if user.role not in ("utility", "admin", "aggregator"):
        raise HTTPException(status_code=403, detail="Insufficient role")
    zone = db.query(GridZone).filter(GridZone.code == body.zone_code).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    for f in db.query(Feeder).filter(Feeder.zone_id == zone.id):
        f.current_loading_mw = f.capacity_mw * body.loading_factor
    db.commit()
    return {"ok": True, "zone": zone.code, "loading_factor": body.loading_factor}


# ----- Participants / flexibility -----
@router.get("/participants")
def list_participants(db: Annotated[Session, Depends(get_db)]) -> list[dict[str, Any]]:
    rows = db.query(Participant).limit(200).all()
    return [
        {
            "id": p.id,
            "name": p.name,
            "category": p.category,
            "zone_id": p.zone_id,
            "baseload_kw": p.baseload_kw,
            "flexible_kw": p.flexible_kw,
            "curtailable_kw": p.curtailable_kw,
            "solar_kw": p.solar_kw,
            "battery_kwh": p.battery_kwh,
            "battery_soc": p.battery_soc,
        }
        for p in rows
    ]


@router.post("/participants")
def create_participant(
    body: ParticipantCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    zone = db.query(GridZone).filter(GridZone.code == body.zone_code).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    feeder = db.query(Feeder).filter(Feeder.zone_id == zone.id).first()
    p = Participant(
        user_id=user.id,
        name=body.name,
        category=body.category,
        zone_id=zone.id,
        feeder_id=feeder.id if feeder else None,
        baseload_kw=body.baseload_kw,
        flexible_kw=body.flexible_kw,
        curtailable_kw=body.curtailable_kw,
        solar_kw=body.solar_kw,
        battery_kwh=body.battery_kwh,
        battery_soc=0.5,
    )
    db.add(p)
    db.flush()
    db.add(
        Meter(
            participant_id=p.id,
            meter_serial=f"SIM-{p.id[:8].upper()}",
            is_simulated=True,
            last_seen_at=datetime.utcnow(),
            status="online",
        )
    )
    db.commit()
    db.refresh(p)
    return {"id": p.id, "name": p.name, "category": p.category}


@router.get("/flexibility/example", response_model=FlexibilityBreakdown)
def flex_example() -> FlexibilityBreakdown:
    return household_example()


@router.get("/flexibility/{participant_id}", response_model=FlexibilityBreakdown)
def flex_for_participant(
    participant_id: str, db: Annotated[Session, Depends(get_db)]
) -> FlexibilityBreakdown:
    p = db.query(Participant).filter(Participant.id == participant_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    return classify_participant(p)


# ----- Marketplace -----
@router.get("/market/offers", response_model=list[OfferOut])
def list_offers(db: Annotated[Session, Depends(get_db)]) -> list[FlexibilityOffer]:
    return db.query(FlexibilityOffer).order_by(FlexibilityOffer.created_at.desc()).limit(100).all()


@router.get("/market/bids", response_model=list[BidOut])
def list_bids(db: Annotated[Session, Depends(get_db)]) -> list[FlexibilityBid]:
    return db.query(FlexibilityBid).order_by(FlexibilityBid.created_at.desc()).limit(100).all()


@router.get("/market/transactions", response_model=list[TransactionOut])
def list_transactions(db: Annotated[Session, Depends(get_db)]) -> list[MarketTransaction]:
    return (
        db.query(MarketTransaction)
        .order_by(MarketTransaction.created_at.desc())
        .limit(100)
        .all()
    )


@router.get("/market/summary", response_model=MarketSummary)
def market_summary(
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MarketSummary:
    offers = db.query(FlexibilityOffer).filter(FlexibilityOffer.status.in_(["open", "partially_filled"])).count()
    bids = db.query(FlexibilityBid).filter(FlexibilityBid.status.in_(["open", "partially_filled"])).count()
    txs = db.query(MarketTransaction).all()
    traded = sum(t.energy_kwh for t in txs)
    price = (
        sum(t.clearing_price * t.energy_kwh for t in txs) / traded
        if traded
        else settings.normal_price_pkr
    )
    return MarketSummary(
        active_offers=offers,
        active_bids=bids,
        cleared_transactions=len(txs),
        current_flexibility_price=round(price, 2),
        total_traded_energy_kwh=round(traded, 2),
    )


@router.post("/market/offers", response_model=OfferOut)
def create_offer(
    body: OfferCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> FlexibilityOffer:
    p = db.query(Participant).filter(Participant.id == body.participant_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found")
    energy = body.power_kw * body.duration_hours
    if body.claimed_meter_delta_kwh is not None:
        verify_flexibility_claim(
            db, p.id, body.claimed_meter_delta_kwh, body.claimed_meter_delta_kwh
        )
    offer = FlexibilityOffer(
        participant_id=p.id,
        seller_user_id=user.id,
        zone_id=p.zone_id,
        feeder_id=body.feeder_id or p.feeder_id,
        flexibility_type=body.flexibility_type,
        power_kw=body.power_kw,
        duration_hours=body.duration_hours,
        energy_kwh=energy,
        available_from=body.available_from,
        available_to=body.available_to,
        min_price_pkr_per_kwh=body.min_price_pkr_per_kwh,
        remaining_kw=body.power_kw,
        status="open",
        meter_evidence_ref=body.meter_evidence_ref,
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


@router.post("/market/bids", response_model=BidOut)
def create_bid(
    body: BidCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> FlexibilityBid:
    zone = db.query(GridZone).filter(GridZone.id == body.zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    bid = FlexibilityBid(
        buyer_user_id=user.id,
        zone_id=body.zone_id,
        feeder_id=body.feeder_id,
        power_kw=body.power_kw,
        duration_hours=body.duration_hours,
        energy_kwh=body.power_kw * body.duration_hours,
        needed_from=body.needed_from,
        needed_to=body.needed_to,
        max_price_pkr_per_kwh=body.max_price_pkr_per_kwh,
        remaining_kw=body.power_kw,
        status="open",
        urgency=body.urgency,
    )
    db.add(bid)
    db.commit()
    db.refresh(bid)
    return bid


@router.post("/market/clear", response_model=ClearMarketResult)
def clear_market(
    body: ClearMarketRequest,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClearMarketResult:
    if user.role not in ("utility", "admin", "aggregator"):
        raise HTTPException(status_code=403, detail="Insufficient role to clear market")
    return clear_zone(db, settings, body.zone_id)


@router.get("/market/clearing-example")
def clearing_example() -> dict[str, Any]:
    return clear_example_scenario()


# ----- Wallet / consumer -----
@router.get("/wallet/me", response_model=WalletOut)
def my_wallet(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> WalletOut:
    w = get_or_create_wallet(db, user.id)
    db.commit()
    return WalletOut(
        user_id=user.id,
        flexibility_provided_kwh=w.flexibility_provided_kwh,
        demand_reduction_kwh=w.demand_reduction_kwh,
        solar_surplus_kwh=w.solar_surplus_kwh,
        earnings_pkr=w.earnings_pkr,
        pending_settlement_pkr=w.pending_settlement_pkr,
    )


@router.get("/consumer/dashboard")
def consumer_dashboard(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    p = db.query(Participant).filter(Participant.user_id == user.id).first()
    flex = classify_participant(p) if p else household_example()
    w = get_or_create_wallet(db, user.id)
    db.commit()
    return {
        "user": UserOut.model_validate(user),
        "flexibility": flex,
        "wallet": WalletOut(
            user_id=user.id,
            flexibility_provided_kwh=w.flexibility_provided_kwh or 125,
            demand_reduction_kwh=w.demand_reduction_kwh or 40,
            solar_surplus_kwh=w.solar_surplus_kwh or 85,
            earnings_pkr=w.earnings_pkr or 1350,
            pending_settlement_pkr=w.pending_settlement_pkr or 250,
        ),
        "today_consumption_kwh": round(flex.current_load_kw * 18, 1),
        "co2_avoided_kg": round((w.flexibility_provided_kwh or 125) * 0.4, 1),
        "peak_contribution_kw": flex.peak_demand_kw,
        "message": "Use electricity more intelligently — shift, store, and coordinate.",
    }


@router.get("/aggregator/dashboard")
def aggregator_dashboard(
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, Any]:
    # Virtual power resource narrative
    households = settings.sim_households
    per_kw = 0.5
    total_mw = households * per_kw / 1000.0
    offers = (
        db.query(FlexibilityOffer)
        .filter(FlexibilityOffer.seller_user_id == user.id)
        .all()
    )
    return {
        "aggregator": UserOut.model_validate(user),
        "pooled_households": households,
        "flexibility_per_household_kw": per_kw,
        "aggregated_flexibility_mw": total_mw,
        "active_offers": len(offers),
        "offer_volume_kw": sum(o.remaining_kw for o in offers),
        "narrative": (
            f"{households:,} households × {per_kw} kW = {total_mw:.1f} MW "
            "virtual flexibility resource."
        ),
    }


# ----- Pricing / optimization / AI / fraud -----
@router.get("/pricing/daily", response_model=list[PricePoint])
def daily_prices(
    settings: Annotated[Settings, Depends(get_settings)],
) -> list[PricePoint]:
    demand = [800 + 400 * ((h / 23) ** 1.2) + (350 if 18 <= h <= 21 else 0) for h in range(24)]
    solar = [max(0, 300 * (1 - abs(h - 13) / 7)) for h in range(24)]
    flex = [d * 0.1 for d in demand]
    return simulate_daily_prices(demand, solar, flex, 1400, settings)


@router.post("/optimize/load-shift", response_model=LoadShiftResult)
def load_shift(body: LoadShiftRequest) -> LoadShiftResult:
    return optimize_load_shift(body)


@router.get("/ai/forecasts")
def ai_forecasts() -> dict[str, Any]:
    return forecast_all()


@router.get("/ai/forecasts/{forecast_type}", response_model=ForecastOut)
def ai_forecast_type(forecast_type: str, horizon: str = "24h") -> ForecastOut:
    data = forecast_all()
    if forecast_type not in data:
        raise HTTPException(status_code=404, detail="Unknown forecast type")
    block = data[forecast_type]
    values = block["horizons"].get(horizon)
    if values is None:
        raise HTTPException(status_code=400, detail="Invalid horizon")
    return ForecastOut(
        forecast_type=forecast_type,
        horizon=horizon,
        values=values,
        model_name=block["model_name"],
    )


@router.get("/ai/anomalies")
def ai_anomalies() -> dict[str, Any]:
    return isolation_forest_scores()


@router.get("/fraud/alerts", response_model=list[FraudAlertOut])
def fraud_alerts(db: Annotated[Session, Depends(get_db)]) -> list[FraudAlert]:
    return db.query(FraudAlert).order_by(FraudAlert.created_at.desc()).limit(50).all()


@router.post("/fraud/check")
def fraud_check(
    participant_id: str,
    claimed_kwh: float,
    observed_kwh: float,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    alert = verify_flexibility_claim(db, participant_id, claimed_kwh, observed_kwh)
    if alert:
        return {"flagged": True, "alert": FraudAlertOut.model_validate(alert)}
    return {"flagged": False, "message": "Claim within plausible bounds"}


# ----- Simulation -----
@router.post("/simulation/run", response_model=SimulationResult)
def simulation_run(
    cfg: SimulationConfig | None = None,
    db: Session = Depends(get_db),
    user: User | None = Depends(get_optional_user),
    settings: Settings = Depends(get_settings),
) -> SimulationResult:
    return run_pakistan_simulation(db, cfg, settings)


@router.get("/simulation/latest", response_model=SimulationResult | None)
def simulation_latest(db: Annotated[Session, Depends(get_db)]) -> SimulationResult | None:
    run = db.query(SimulationRun).order_by(SimulationRun.created_at.desc()).first()
    if not run:
        return None
    # Re-run with stored config for full curves (idempotent demo)
    cfg = SimulationConfig(**run.config)
    return run_pakistan_simulation(db, cfg)


# ----- DR / admin config -----
@router.get("/dr/events")
def dr_events(db: Annotated[Session, Depends(get_db)]) -> list[dict[str, Any]]:
    rows = db.query(DemandResponseEvent).all()
    return [
        {
            "id": e.id,
            "zone_id": e.zone_id,
            "title": e.title,
            "starts_at": e.starts_at.isoformat(),
            "ends_at": e.ends_at.isoformat(),
            "target_reduction_mw": e.target_reduction_mw,
            "achieved_reduction_mw": e.achieved_reduction_mw,
            "status": e.status,
        }
        for e in rows
    ]


@router.post("/dr/events")
def create_dr(
    body: DREventCreate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict[str, Any]:
    if user.role not in ("utility", "admin"):
        raise HTTPException(status_code=403, detail="Insufficient role")
    e = DemandResponseEvent(**body.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return {"id": e.id, "title": e.title, "status": e.status}


@router.get("/admin/config")
def get_config(settings: Annotated[Settings, Depends(get_settings)]) -> dict[str, float]:
    return {
        "platform_fee_pct": settings.platform_fee_pct,
        "grid_fee_pct": settings.grid_fee_pct,
        "normal_price_pkr": settings.normal_price_pkr,
        "peak_price_pkr": settings.peak_price_pkr,
        "critical_price_pkr": settings.critical_price_pkr,
    }


@router.put("/admin/config")
def update_config(
    body: ConfigUpdate,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[User, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> dict[str, float]:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin only")
    data = body.model_dump(exclude_none=True)
    for k, v in data.items():
        setattr(settings, k, v)
        row = db.query(PlatformConfig).filter(PlatformConfig.key == k).first()
        if row:
            row.value = v
        else:
            db.add(PlatformConfig(key=k, value=v))
    db.commit()
    get_settings.cache_clear()
    return get_config(get_settings())


# ----- WebSocket heartbeat -----
class ConnectionManager:
    def __init__(self) -> None:
        self.active: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active.append(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active:
            self.active.remove(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        for ws in list(self.active):
            try:
                await ws.send_json(message)
            except Exception:
                self.disconnect(ws)


manager = ConnectionManager()


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket) -> None:
    await manager.connect(websocket)
    try:
        await websocket.send_json(
            {
                "type": "hello",
                "message": "GRIDFLEX live channel",
                "ts": datetime.utcnow().isoformat(),
            }
        )
        while True:
            data = await websocket.receive_text()
            await websocket.send_json({"type": "echo", "data": data})
    except WebSocketDisconnect:
        manager.disconnect(websocket)