"""Zone-constrained market clearing engine."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from app.config import Settings
from app.models import FlexibilityBid, FlexibilityOffer, MarketTransaction
from app.schemas import ClearMarketResult, TransactionOut
from app.services.settlement import apply_settlement


@dataclass
class ClearedMatch:
    offer: FlexibilityOffer
    bid: FlexibilityBid
    power_kw: float
    clearing_price: float


def _windows_overlap(
    a_from: datetime, a_to: datetime, b_from: datetime, b_to: datetime
) -> bool:
    return a_from < b_to and b_from < a_to


def _compatible(offer: FlexibilityOffer, bid: FlexibilityBid) -> bool:
    """Geographic/grid constraints: same zone; feeder match if both specify."""
    if offer.zone_id != bid.zone_id:
        return False
    if offer.feeder_id and bid.feeder_id and offer.feeder_id != bid.feeder_id:
        return False
    if offer.min_price_pkr_per_kwh > bid.max_price_pkr_per_kwh:
        return False
    if offer.remaining_kw <= 0 or bid.remaining_kw <= 0:
        return False
    if offer.status not in ("open", "partially_filled"):
        return False
    if bid.status not in ("open", "partially_filled"):
        return False
    return _windows_overlap(
        offer.available_from, offer.available_to, bid.needed_from, bid.needed_to
    )


def clear_zone(
    db: Session,
    settings: Settings,
    zone_id: str | None = None,
) -> ClearMarketResult:
    """
    Merit-order clearing within a zone (or all zones sequentially).

    Sellers sorted ascending by min price; buyers descending by max price.
    Pay-as-clear within each matched pair uses mid/clearing = offer price
    when offer <= bid max (uniform within matched tranche = offer ask).
    """
    offer_q = db.query(FlexibilityOffer).filter(
        FlexibilityOffer.status.in_(["open", "partially_filled"]),
        FlexibilityOffer.remaining_kw > 0,
    )
    bid_q = db.query(FlexibilityBid).filter(
        FlexibilityBid.status.in_(["open", "partially_filled"]),
        FlexibilityBid.remaining_kw > 0,
    )
    if zone_id:
        offer_q = offer_q.filter(FlexibilityOffer.zone_id == zone_id)
        bid_q = bid_q.filter(FlexibilityBid.zone_id == zone_id)

    offers = sorted(offer_q.all(), key=lambda o: (o.min_price_pkr_per_kwh, o.created_at))
    bids = sorted(
        bid_q.all(),
        key=lambda b: (-b.max_price_pkr_per_kwh, 0 if b.urgency == "critical" else 1, b.created_at),
    )

    matches: list[ClearedMatch] = []
    for bid in bids:
        if bid.remaining_kw <= 0:
            continue
        for offer in offers:
            if not _compatible(offer, bid):
                continue
            qty = min(offer.remaining_kw, bid.remaining_kw)
            if qty <= 0:
                continue
            # Pay-as-clear: use offer price when within bid willingness
            clearing = offer.min_price_pkr_per_kwh
            matches.append(ClearedMatch(offer, bid, qty, clearing))
            offer.remaining_kw = round(offer.remaining_kw - qty, 6)
            bid.remaining_kw = round(bid.remaining_kw - qty, 6)
            offer.status = "filled" if offer.remaining_kw <= 1e-6 else "partially_filled"
            bid.status = "filled" if bid.remaining_kw <= 1e-6 else "partially_filled"
            if bid.remaining_kw <= 1e-6:
                break

    transactions: list[MarketTransaction] = []
    for m in matches:
        duration = min(m.offer.duration_hours, m.bid.duration_hours)
        energy = m.power_kw * duration
        gross = energy * m.clearing_price
        platform_fee = gross * settings.platform_fee_pct
        grid_fee = gross * settings.grid_fee_pct
        seller_net = gross - platform_fee - grid_fee

        tx = MarketTransaction(
            offer_id=m.offer.id,
            bid_id=m.bid.id,
            seller_user_id=m.offer.seller_user_id,
            buyer_user_id=m.bid.buyer_user_id,
            zone_id=m.offer.zone_id,
            feeder_id=m.offer.feeder_id or m.bid.feeder_id,
            power_kw=m.power_kw,
            energy_kwh=energy,
            offer_price=m.offer.min_price_pkr_per_kwh,
            clearing_price=m.clearing_price,
            seller_revenue_pkr=round(seller_net, 2),
            buyer_cost_pkr=round(gross, 2),
            platform_fee_pkr=round(platform_fee, 2),
            grid_fee_pkr=round(grid_fee, 2),
            status="cleared",
            verification_status="pending",
            meter_evidence={
                "offer_evidence": m.offer.meter_evidence_ref,
                "flexibility_type": m.offer.flexibility_type,
            },
        )
        # Blockchain-ready optional hash (not a live chain)
        raw = f"{tx.offer_id}:{tx.bid_id}:{tx.power_kw}:{tx.clearing_price}:{datetime.utcnow().isoformat()}"
        tx.blockchain_hash = hashlib.sha256(raw.encode()).hexdigest()
        db.add(tx)
        transactions.append(tx)

    db.flush()
    for tx in transactions:
        apply_settlement(db, tx)

    db.commit()
    for tx in transactions:
        db.refresh(tx)

    cleared_kw = sum(t.power_kw for t in transactions)
    cleared_kwh = sum(t.energy_kwh for t in transactions)
    clearing_price = (
        sum(t.clearing_price * t.energy_kwh for t in transactions) / cleared_kwh
        if cleared_kwh
        else None
    )

    return ClearMarketResult(
        cleared_volume_kw=round(cleared_kw, 3),
        cleared_energy_kwh=round(cleared_kwh, 3),
        clearing_price=round(clearing_price, 3) if clearing_price is not None else None,
        transaction_count=len(transactions),
        total_seller_revenue_pkr=round(sum(t.seller_revenue_pkr for t in transactions), 2),
        total_buyer_cost_pkr=round(sum(t.buyer_cost_pkr for t in transactions), 2),
        total_platform_fee_pkr=round(sum(t.platform_fee_pkr for t in transactions), 2),
        total_grid_fee_pkr=round(sum(t.grid_fee_pkr for t in transactions), 2),
        transactions=[TransactionOut.model_validate(t) for t in transactions],
    )


def clear_example_scenario() -> dict:
    """Documented example: 400 kW demand max PKR 12 vs offers 8/9/11."""
    offers = [
        {"name": "A", "kw": 100, "price": 8},
        {"name": "B", "kw": 200, "price": 9},
        {"name": "C", "kw": 300, "price": 11},
    ]
    demand = 400
    max_price = 12
    selected = []
    remaining = demand
    for o in offers:
        if o["price"] > max_price:
            continue
        take = min(o["kw"], remaining)
        selected.append({**o, "cleared_kw": take})
        remaining -= take
        if remaining <= 0:
            break
    cleared = demand - remaining
    # Pay-as-clear: highest accepted offer price
    clearing_price = max((s["price"] for s in selected), default=None)
    energy = cleared * 2  # assume 2h
    buyer_cost = energy * clearing_price if clearing_price else 0
    platform_fee = buyer_cost * 0.05
    grid_fee = buyer_cost * 0.02
    seller_revenue = buyer_cost - platform_fee - grid_fee
    return {
        "cleared_volume_kw": cleared,
        "clearing_price": clearing_price,
        "seller_revenue_pkr": round(seller_revenue, 2),
        "buyer_cost_pkr": round(buyer_cost, 2),
        "platform_fee_pkr": round(platform_fee, 2),
        "grid_fee_pkr": round(grid_fee, 2),
        "selected": selected,
    }